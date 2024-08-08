terraform {
  required_providers {
    grafana = {
      source = "grafana/grafana"
    }
  }
}

provider "grafana" {
  url  = "http://localhost:3000"
  auth = "admin:admin" # Default credentials, change if you've modified them
}

resource "grafana_folder" "metrics_folder" {
  title = "The folder containing metrics for the droughtwatch project"
}

resource "grafana_data_source" "postgres_droughtwatch" {

  type          = "postgres"
  name          = "postgres-droughtwatch"
  url           = "localhost:5432"
  database_name = var.db_name
  username      = var.db_username
  secure_json_data_encoded = jsonencode({
    password = var.db_password
  })
  json_data_encoded = jsonencode({
    postgres_version = 15
  })

}

# Using a JSON file
resource "grafana_dashboard" "metrics_dashboard" {

  config_json = templatefile("dashboard_template.json", {
    datasource_uid = grafana_data_source.postgres_droughtwatch.uid
  })
  folder = grafana_folder.metrics_folder.id
}


resource "grafana_rule_group" "rule_group_0000" {
  org_id           = 1
  name             = "RED alert"
  folder_uid       = grafana_folder.metrics_folder.uid
  interval_seconds = 10

  rule {
    name      = "Prediction_drift"
    condition = "C"

    data {
      ref_id = "prediction-drift"

      relative_time_range {
        from = 600
        to   = 0
      }

      datasource_uid = grafana_data_source.postgres_droughtwatch.uid
      model          = "{\"editorMode\":\"code\",\"format\":\"table\",\"intervalMs\":1000,\"maxDataPoints\":43200,\"rawQuery\":true,\"rawSql\":\"select max(prediction_drift) from metrics;\",\"refId\":\"prediction-drift\",\"sql\":{\"columns\":[{\"parameters\":[],\"type\":\"function\"}],\"groupBy\":[{\"property\":{\"type\":\"string\"},\"type\":\"groupBy\"}],\"limit\":50}}"
    }
    data {
      ref_id = "C"

      relative_time_range {
        from = 600
        to   = 0
      }

      datasource_uid = "__expr__"
      model          = "{\"conditions\":[{\"evaluator\":{\"params\":[0.25],\"type\":\"gt\"},\"operator\":{\"type\":\"and\"},\"query\":{\"params\":[\"C\"]},\"reducer\":{\"params\":[],\"type\":\"last\"},\"type\":\"query\"}],\"datasource\":{\"type\":\"__expr__\",\"uid\":\"__expr__\"},\"expression\":\"prediction-drift\",\"intervalMs\":1000,\"maxDataPoints\":43200,\"refId\":\"C\",\"type\":\"threshold\"}"
    }

    no_data_state  = "NoData"
    exec_err_state = "Error"
    for            = "1m"
    annotations = {
      __dashboardUid__ = grafana_dashboard.metrics_dashboard.uid
      __panelId__      = "1"
    }
    labels    = {}
    is_paused = false

    notification_settings {
      contact_point = "grafana-default-email"
      group_by      = null
      mute_timings  = null
    }
  }
}
