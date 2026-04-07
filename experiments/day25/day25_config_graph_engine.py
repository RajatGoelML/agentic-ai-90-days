

GRAPH_CONFIG = {

  "START":{"handler":"day25_config_graph_engine.py","next":["LOAD_APPLICATION"]},
  "LOAD_APPLICATION": {
  "handler": "load_application_handler",
  "next": ["DETERMINISTIC_SCORING"]
 },

 "DETERMINISTIC_SCORING": {
  "handler": "deterministic_scoring_handler",
  "next": ["AI_RISK_REVIEW"]
 },

 "AI_RISK_REVIEW": {
  "handler": "ai_risk_review_handler",
  "next": ["TOOL_EXECUTION"]
 },

 "TOOL_EXECUTION": {
  "handler": "tool_execution_handler",
  "next": ["FRAUD_CHECK","CREDIT_LOOKUP","SECTOR_RISK","AGGREGATE_RESULTS"]
 },

 "FRAUD_CHECK": {
  "handler": "fraud_check_handler",
  "next": ["TOOL_EXECUTION"]
 },

 "CREDIT_LOOKUP": {
  "handler": "credit_lookup_handler",
  "next": ["TOOL_EXECUTION"]
 },

 "SECTOR_RISK": {
  "handler": "sector_risk_handler",
  "next": ["TOOL_EXECUTION"]
 },

 "AGGREGATE_RESULTS": {
  "handler": "aggregate_results_handler",
  "next": ["POLICY_CHECK"]
 },

 "POLICY_CHECK": {
  "handler": "policy_check_handler",
  "next": ["FINAL_DECISION"]
 },

 "FINAL_DECISION": {
  "handler": "final_decision_handler",
  "next": ["END"]
 },

 "END": {
  "handler": "end_handler",
  "next": []
 }
}