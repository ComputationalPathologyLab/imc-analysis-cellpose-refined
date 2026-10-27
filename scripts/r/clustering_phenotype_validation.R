#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
  library(pheatmap)
  library(viridis)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 13) {
  stop(
    "Usage: clustering_phenotype_validation.R <features.csv> <phenotypes.csv> <panel.csv> ",
    "<output_cells.csv> <output_summary.csv> <output_overlap.csv> <heatmap.png> ",
    "<overlap_heatmap.png> <snn_k> <phenograph_k> <som_max_k> <som_meta_k> <sample_cells>"
  )
}

features_path <- args[[1]]
phenotypes_path <- args[[2]]
panel_path <- args[[3]]
output_cells_path <- args[[4]]
output_summary_path <- args[[5]]
output_overlap_path <- args[[6]]
heatmap_path <- args[[7]]
overlap_heatmap_path <- args[[8]]
snn_k <- as.integer(args[[9]])
phenograph_k <- as.integer(args[[10]])
som_max_k <- as.integer(args[[11]])
som_meta_k <- as.integer(args[[12]])
sample_cells <- as.integer(args[[13]])

read_required_csv <- function(path) {
  if (!file.exists(path)) {
    stop("Required input not found: ", path)
  }
  read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
}

safe_name <- function(x) {
  make.names(x, unique = TRUE)
}

features <- read_required_csv(features_path)
phenotypes <- read_required_csv(phenotypes_path)
panel <- read_required_csv(panel_path)

required_identity <- c("Image", "Object")
missing_identity <- setdiff(required_identity, colnames(features))
if (length(missing_identity) > 0) {
  stop("Feature table missing required columns: ", paste(missing_identity, collapse = ", "))
}

missing_phenotype <- setdiff(c("Image", "Object", "category", "phenotype"), colnames(phenotypes))
if (length(missing_phenotype) > 0) {
  stop("Phenotype table missing required columns: ", paste(missing_phenotype, collapse = ", "))
}

if (!"name" %in% colnames(panel)) {
  stop("Panel table must contain a 'name' column.")
}

panel_markers <- unique(panel$name[panel$name != ""])
excluded_markers <- c("DNA1", "DNA2", "191Ir", "193Ir", "80ArAr", "127I", "131Xe", "134Xe", "138Ba", "208Pb")
candidate_markers <- setdiff(panel_markers, excluded_markers)
marker_columns <- candidate_markers[candidate_markers %in% colnames(features)]

if (length(marker_columns) < 2) {
  stop("At least two biological marker columns are required for clustering validation.")
}

features$.cell_key <- paste(features$Image, features$Object, sep = "||")
phenotypes$.cell_key <- paste(phenotypes$Image, phenotypes$Object, sep = "||")

matched <- merge(
  features,
  phenotypes[, c(".cell_key", "category", "phenotype")],
  by = ".cell_key",
  all.x = FALSE,
  all.y = FALSE,
  sort = FALSE
)

if (nrow(matched) == 0) {
  stop("No matching cells found between feature and phenotype tables.")
}

expr <- as.matrix(matched[, marker_columns, drop = FALSE])
storage.mode(expr) <- "numeric"
expr[!is.finite(expr)] <- 0

scaled_expr <- scale(expr)
scaled_expr[!is.finite(scaled_expr)] <- 0

cluster_availability <- data.frame(
  method = c("Rphenograph", "SNN_louvain", "CATALYST_SOM"),
  package_available = c(
    requireNamespace("Rphenograph", quietly = TRUE) && requireNamespace("igraph", quietly = TRUE),
    requireNamespace("scran", quietly = TRUE) && requireNamespace("bluster", quietly = TRUE),
    requireNamespace("CATALYST", quietly = TRUE) && requireNamespace("SingleCellExperiment", quietly = TRUE)
  ),
  stringsAsFactors = FALSE
)

cluster_columns <- c()

if (cluster_availability$package_available[cluster_availability$method == "Rphenograph"]) {
  set.seed(230619)
  phenograph_out <- Rphenograph::Rphenograph(scaled_expr, k = phenograph_k)
  matched$phenograph_cluster <- as.character(igraph::membership(phenograph_out[[2]]))
  cluster_columns <- c(cluster_columns, "phenograph_cluster")
} else {
  matched$phenograph_cluster <- NA_character_
}

if (cluster_availability$package_available[cluster_availability$method == "SNN_louvain"]) {
  set.seed(220620)
  matched$snn_louvain_cluster <- as.character(
    bluster::clusterRows(
      scaled_expr,
      BLUSPARAM = bluster::SNNGraphParam(k = snn_k, cluster.fun = "louvain", type = "jaccard")
    )
  )
  cluster_columns <- c(cluster_columns, "snn_louvain_cluster")
} else {
  matched$snn_louvain_cluster <- NA_character_
}

if (cluster_availability$package_available[cluster_availability$method == "CATALYST_SOM"]) {
  suppressPackageStartupMessages({
    library(SingleCellExperiment)
  })
  sce <- SingleCellExperiment::SingleCellExperiment(
    assays = list(exprs = t(expr))
  )
  rownames(sce) <- marker_columns
  colnames(sce) <- matched$.cell_key
  rowData(sce)$marker_name <- marker_columns
  rowData(sce)$use_channel <- TRUE

  set.seed(220410)
  max_k <- max(som_meta_k, min(som_max_k, max(2, som_meta_k)))
  sce <- CATALYST::cluster(sce, features = marker_columns, xdim = 10, ydim = 10, maxK = max_k, seed = 220410)
  cluster_id <- paste0("meta", som_meta_k)
  matched$som_cluster <- as.character(CATALYST::cluster_ids(sce, cluster_id))
  cluster_columns <- c(cluster_columns, "som_cluster")
} else {
  matched$som_cluster <- NA_character_
}

if (length(cluster_columns) == 0) {
  stop("No clustering package set is available. Install Rphenograph or ensure scran/bluster/CATALYST are available.")
}

identity_metadata_columns <- intersect(
  c("phenotype_confidence", "phenotype_basis", "lineage_class", "state_flags", "review_priority"),
  colnames(matched)
)
cell_output <- matched[, c("Image", "Object", "category", "phenotype", identity_metadata_columns, "phenograph_cluster", "snn_louvain_cluster", "som_cluster"), drop = FALSE]
write.csv(cell_output, output_cells_path, row.names = FALSE)

summary_rows <- list()
for (cluster_col in cluster_columns) {
  tab <- table(matched[[cluster_col]], matched$phenotype)
  for (cluster_id in rownames(tab)) {
    counts <- tab[cluster_id, ]
    total <- sum(counts)
    dominant <- names(which.max(counts))
    if ("review_priority" %in% colnames(matched)) {
      review_values <- matched[matched[[cluster_col]] == cluster_id, "review_priority"]
      high_review_count <- sum(review_values == "High", na.rm = TRUE)
    } else {
      high_review_count <- NA_integer_
    }
    summary_rows[[length(summary_rows) + 1]] <- data.frame(
      method = cluster_col,
      cluster_id = cluster_id,
      cell_count = total,
      dominant_phenotype = dominant,
      dominant_phenotype_count = as.integer(max(counts)),
      dominant_phenotype_fraction = as.numeric(max(counts) / total),
      high_review_priority_count = as.integer(high_review_count),
      high_review_priority_fraction = as.numeric(ifelse(is.na(high_review_count), NA_real_, high_review_count / total)),
      marker_count_used = length(marker_columns),
      stringsAsFactors = FALSE
    )
  }
}
summary_table <- do.call(rbind, summary_rows)
availability_rows <- data.frame(
  method = paste0("availability_", cluster_availability$method),
  cluster_id = ifelse(cluster_availability$package_available, "available", "not_available"),
  cell_count = nrow(matched),
  dominant_phenotype = "",
  dominant_phenotype_count = NA_integer_,
  dominant_phenotype_fraction = NA_real_,
  high_review_priority_count = NA_integer_,
  high_review_priority_fraction = NA_real_,
  marker_count_used = length(marker_columns),
  stringsAsFactors = FALSE
)
summary_table <- rbind(summary_table, availability_rows)
write.csv(summary_table, output_summary_path, row.names = FALSE)

overlap_rows <- list()
for (cluster_col in cluster_columns) {
  tab <- table(matched[[cluster_col]], matched$phenotype)
  for (cluster_id in rownames(tab)) {
    total <- sum(tab[cluster_id, ])
    for (phenotype_name in colnames(tab)) {
      count <- as.integer(tab[cluster_id, phenotype_name])
      if (count > 0) {
        overlap_rows[[length(overlap_rows) + 1]] <- data.frame(
          method = cluster_col,
          cluster_id = cluster_id,
          phenotype = phenotype_name,
          cell_count = count,
          fraction_of_cluster = count / total,
          stringsAsFactors = FALSE
        )
      }
    }
  }
}
overlap_table <- do.call(rbind, overlap_rows)
write.csv(overlap_table, output_overlap_path, row.names = FALSE)

set.seed(220619)
sample_index <- seq_len(nrow(matched))
if (length(sample_index) > sample_cells) {
  sample_index <- sample(sample_index, sample_cells)
}

heatmap_method <- if ("snn_louvain_cluster" %in% cluster_columns) "snn_louvain_cluster" else cluster_columns[[1]]
cluster_means <- aggregate(expr, by = list(cluster = matched[[heatmap_method]]), FUN = mean)
rownames(cluster_means) <- cluster_means$cluster
cluster_means$cluster <- NULL
cluster_means <- as.matrix(cluster_means)
cluster_means_scaled <- t(scale(t(cluster_means)))
cluster_means_scaled[!is.finite(cluster_means_scaled)] <- 0

png(heatmap_path, width = 1800, height = 1200, res = 180)
pheatmap::pheatmap(
  cluster_means_scaled,
  color = viridis::viridis(100),
  main = paste("Marker expression by", heatmap_method),
  fontsize_row = 7,
  fontsize_col = 7
)
dev.off()

overlap_for_plot <- subset(overlap_table, method == heatmap_method)
if (nrow(overlap_for_plot) > 0) {
  overlap_matrix <- xtabs(cell_count ~ cluster_id + phenotype, data = overlap_for_plot)
  overlap_matrix <- log10(overlap_matrix + 1)
  png(overlap_heatmap_path, width = 1800, height = 1200, res = 180)
  pheatmap::pheatmap(
    overlap_matrix,
    color = viridis::viridis(100),
    main = paste("Cluster-to-phenotype overlap:", heatmap_method),
    fontsize_row = 7,
    fontsize_col = 7
  )
  dev.off()
}

cat("Clustering validation completed with methods:", paste(cluster_columns, collapse = ", "), "\n")
cat("Markers used:", paste(marker_columns, collapse = ", "), "\n")
