# Single master DynamoDB table for NSE LLM Trader.
# All entity types (POSITION, DECISION, TRADE, NAV) share this table,
# separated by PK/SK prefix conventions. On-demand billing. TTL enabled.
#
# PK/SK layout:
#   POSITION  PK=TICKER#{symbol}   SK=DATE#{yyyy-mm-dd}
#   DECISION  PK=DATE#{yyyy-mm-dd} SK=TICKER#{symbol}#AGENT#{name}
#   TRADE     PK=DATE#{yyyy-mm-dd} SK=TRADE#{uuid}
#   NAV       PK=DATE#{yyyy-mm-dd} SK=PORTFOLIO

resource "aws_dynamodb_table" "master" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false  # cost control; enable in Phase 2
  }

  tags = {
    Name = "${var.name_prefix}-master"
  }
}
