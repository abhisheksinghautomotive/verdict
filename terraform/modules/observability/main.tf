resource "aws_cloudwatch_log_metric_filter" "request_latency" {
  name           = "verdict-app-request-latency"
  pattern        = "{ $.duration_ms = * }"
  log_group_name = var.log_group_name

  metric_transformation {
    name      = "RequestLatency"
    namespace = "verdict-app"
    value     = "$.duration_ms"
  }
}

resource "aws_cloudwatch_log_metric_filter" "request_count" {
  name           = "verdict-app-request-count"
  pattern        = "{ $.message = \"request_completed\" || $.message = \"request_failed\" }"
  log_group_name = var.log_group_name

  metric_transformation {
    name      = "RequestCount"
    namespace = "verdict-app"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "http_5xx_count" {
  name           = "verdict-app-http-5xx-count"
  pattern        = "{ $.status >= 500 }"
  log_group_name = var.log_group_name

  metric_transformation {
    name      = "Http5xxCount"
    namespace = "verdict-app"
    value     = "1"
  }
}
