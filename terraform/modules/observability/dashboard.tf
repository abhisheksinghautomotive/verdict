resource "aws_cloudwatch_dashboard" "verdict" {
  dashboard_name = "verdict-${var.cluster_name}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["verdict-app", "RequestLatency", { "stat" : "p50", "label" : "p50 Latency (ms)", "color" : "#1f77b4" }],
            ["verdict-app", "RequestLatency", { "stat" : "p95", "label" : "p95 Latency (ms)", "color" : "#ff7f0e" }],
            ["verdict-app", "RequestLatency", { "stat" : "p99", "label" : "p99 Latency (ms)", "color" : "#d62728" }]
          ]
          period = 60
          region = var.aws_region
          title  = "FastAPI Request Latency (p50 / p95 / p99)"
          view   = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["verdict-app", "RequestCount", { "stat" : "Sum", "label" : "Requests/Min", "color" : "#2ca02c" }]
          ]
          period = 60
          region = var.aws_region
          title  = "FastAPI Traffic (Requests/Min)"
          view   = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["verdict-app", "Http5xxCount", { "id" : "m1", "stat" : "Sum", "period" : 60, "visible" : false }],
            ["verdict-app", "RequestCount", { "id" : "m2", "stat" : "Sum", "period" : 60, "visible" : false }],
            [{ "expression" : "(m1 / m2) * 100", "label" : "5xx Error Rate (%)", "id" : "e1", "color" : "#d62728" }]
          ]
          period = 60
          region = var.aws_region
          title  = "FastAPI Error Rate (5xx %)"
          view   = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["ContainerInsights", "pod_cpu_utilization", "ClusterName", var.cluster_name, "Namespace", "verdict", { "stat" : "Average", "label" : "CPU Utilization (%)", "color" : "#1f77b4" }],
            ["ContainerInsights", "pod_memory_utilization", "ClusterName", var.cluster_name, "Namespace", "verdict", { "stat" : "Average", "label" : "Memory Utilization (%)", "color" : "#2ca02c" }]
          ]
          period = 60
          region = var.aws_region
          title  = "Pod Saturation (CPU / Memory %)"
          view   = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["verdict-app", "PipelineDuration", { "stat" : "Average", "label" : "Pipeline Duration (sec)", "color" : "#9467bd" }]
          ]
          period = 60
          region = var.aws_region
          title  = "Pipeline Duration (PR to Gate Result)"
          view   = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["ContainerInsights", "cluster_node_count", "ClusterName", var.cluster_name, { "stat" : "Maximum", "label" : "Node Count", "color" : "#e377c2" }]
          ]
          period = 60
          region = var.aws_region
          title  = "EKS Node Count"
          view   = "timeSeries"
        }
      }
    ]
  })
}
