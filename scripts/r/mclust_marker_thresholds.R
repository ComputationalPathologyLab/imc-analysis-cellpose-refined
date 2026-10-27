#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(mclust)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  stop("Usage: mclust_marker_thresholds.R <marker_values.csv> <thresholds.csv>")
}

input_path <- args[[1]]
output_path <- args[[2]]

values <- read.csv(input_path, stringsAsFactors = FALSE)
required <- c("marker", "value")
missing <- setdiff(required, colnames(values))
if (length(missing) > 0) {
  stop(paste("Missing required columns:", paste(missing, collapse = ", ")))
}

threshold_rows <- list()
for (marker_name in sort(unique(values$marker))) {
  marker_values <- values$value[values$marker == marker_name]
  marker_values <- marker_values[is.finite(marker_values)]

  if (length(marker_values) == 0) {
    threshold <- NA_real_
    status <- "no_finite_values"
  } else if (length(unique(marker_values)) == 1) {
    threshold <- unique(marker_values)[[1]]
    status <- "constant"
  } else {
    fit <- tryCatch(
      Mclust(marker_values, G = 2, verbose = FALSE),
      error = function(e) NULL
    )

    if (is.null(fit) || is.null(fit$classification) || length(unique(fit$classification)) < 2) {
      threshold <- as.numeric(stats::quantile(marker_values, probs = 0.8, names = FALSE, type = 7))
      status <- "mclust_fallback_percentile_80"
    } else {
      component_means <- tapply(marker_values, fit$classification, mean)
      high_component <- as.integer(names(component_means)[which.max(component_means)])
      high_values <- marker_values[fit$classification == high_component]
      low_values <- marker_values[fit$classification != high_component]

      if (length(high_values) == 0 || length(low_values) == 0) {
        threshold <- as.numeric(stats::quantile(marker_values, probs = 0.8, names = FALSE, type = 7))
        status <- "mclust_fallback_percentile_80"
      } else {
        grid <- seq(min(marker_values), max(marker_values), length.out = 1000)
        prediction <- tryCatch(
          predict(fit, newdata = grid),
          error = function(e) NULL
        )

        if (is.null(prediction) || is.null(prediction$z) || ncol(prediction$z) < 2) {
          threshold <- min(high_values)
          status <- "mclust_high_component_minimum"
        } else {
          high_column <- match(as.character(high_component), colnames(prediction$z))
          if (is.na(high_column)) {
            high_column <- high_component
          }

          low_columns <- setdiff(seq_len(ncol(prediction$z)), high_column)
          high_posterior <- prediction$z[, high_column]
          low_posterior <- rowSums(prediction$z[, low_columns, drop = FALSE])
          mean_range <- range(component_means)
          candidate_positions <- which(grid >= mean_range[[1]] & grid <= mean_range[[2]])

          if (length(candidate_positions) == 0) {
            threshold <- min(high_values)
            status <- "mclust_high_component_minimum"
          } else {
            crossing_position <- candidate_positions[
              which.min(abs(high_posterior[candidate_positions] - low_posterior[candidate_positions]))
            ]
            threshold <- grid[[crossing_position]]
            status <- "mclust_posterior_crossing"
          }
        }
      }
    }
  }

  threshold_rows[[length(threshold_rows) + 1]] <- data.frame(
    marker = marker_name,
    threshold_method = "mclust_r",
    positive_threshold = threshold,
    threshold_status = status,
    stringsAsFactors = FALSE
  )
}

thresholds <- do.call(rbind, threshold_rows)
write.csv(thresholds, output_path, row.names = FALSE)
