variable "aws_region" {
  description = "AWS region for the payment reliability queues and alarms."
  type        = string
  default     = "ap-southeast-2"
}

variable "name_prefix" {
  description = "Prefix for queue and alarm names."
  type        = string
  default     = "settlement-guard"
}

variable "parked_settlement_threshold" {
  description = "Alarm when this many settlements are parked for two consecutive minutes."
  type        = number
  default     = 25
}

variable "reconciliation_break_threshold" {
  description = "Alarm when this many reconciliation breaks are recorded in five minutes."
  type        = number
  default     = 50
}
