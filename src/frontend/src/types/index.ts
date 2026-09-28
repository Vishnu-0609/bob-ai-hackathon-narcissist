export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  full_name: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  role: string;
  full_name: string;
}

export interface Incident {
  id: string;
  name: string;
  location: string;
  date: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
  am_count: number;
  pm_count: number;
  matched_count: number;
}

export interface AMCase {
  id: string;
  incident_id: string;
  case_number: string;
  name: string;
  age?: number;
  sex?: string;
  height_cm?: number;
  weight_kg?: number;
  blood_group?: string;
  physical_description?: string;
  scars: any[];
  birthmarks: any[];
  tattoos: any[];
  clothing: any[];
  jewellery: any[];
  dental_notes?: string;
  medical_history?: string;
  implants: any[];
  last_seen_location?: string;
  last_seen_time?: string;
  source?: string;
  source_type?: string;
  provenance_details?: Record<string, any>;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface PMCase {
  id: string;
  incident_id: string;
  body_number: string;
  estimated_age_min?: number;
  estimated_age_max?: number;
  sex?: string;
  height_cm?: number;
  weight_kg?: number;
  blood_group?: string;
  physical_description?: string;
  scars: any[];
  birthmarks: any[];
  tattoos: any[];
  clothing: any[];
  jewellery: any[];
  dental_findings?: string;
  medical_findings?: string;
  implants: any[];
  fingerprint_status: string;
  dna_status: string;
  recovery_location?: string;
  examiner?: string;
  provenance_details?: Record<string, any>;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface MatchEvidenceItem {
  field_name: string;
  am_value?: string;
  pm_value?: string;
  comparison_result: 'MATCH' | 'MISMATCH' | 'UNKNOWN' | 'NOT_AVAILABLE';
  weight: number;
  score_awarded: number;
  contradiction: boolean;
  notes?: string;
  provenance?: Record<string, any>;
}

export interface CandidateMatch {
  match_id?: string;
  am_id: string;
  am_case_number: string;
  am_name: string;
  match_score: number;
  evidence_quality: string;
  data_completeness: number;
  contradiction_status: 'NONE' | 'CONTRADICTION_REVIEW' | 'STRONG_CONTRADICTION';
  candidate_rank: number;
  status: string;
  supporting_evidence: MatchEvidenceItem[];
  contradictions: MatchEvidenceItem[];
  unknown: MatchEvidenceItem[];
  bob_rationale?: string;
  evidence_gaps?: {
    available_evidence: string[];
    missing_evidence: string[];
    unresolved_contradictions: string[];
    recommended_workflow: string[];
    summary: string;
  };
  reconciliation_status: string;
}

export interface TopCandidatesResponse {
  pm_id: string;
  pm_body_number: string;
  candidates: CandidateMatch[];
  total_candidates_evaluated: number;
  calculation_timestamp: string;
}

export interface ReconciliationResponse {
  id: string;
  incident_id: string;
  pm_id: string;
  am_id: string;
  decision: 'CONFIRMED_BY_FORENSIC_TEAM' | 'REJECTED' | 'NEEDS_REVIEW' | 'PENDING_REVIEW';
  reason: string;
  coordinator_comment?: string;
  forensic_notes?: string;
  reviewed_by: string;
  reviewed_at: string;
  created_at: string;
}

export interface ReportResponse {
  id: string;
  report_number: string;
  incident_id: string;
  pm_id: string;
  am_id: string;
  title: string;
  summary?: string;
  content_json: Record<string, any>;
  generated_by: string;
  generated_at: string;
  status: string;
}

export interface AuditLogItem {
  id: string;
  event_id: string;
  user_id: string;
  role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, any>;
  old_value_hash?: string;
  new_value_hash?: string;
  previous_event_hash: string;
  event_hash: string;
  timestamp: string;
}

export interface AuditVerifyResponse {
  valid: boolean;
  events_checked: number;
  broken_at?: string;
  last_event_hash?: string;
  verification_time_ms: number;
}

export interface EvaluationMetrics {
  top1_accuracy: number;
  top3_recall: number;
  contradiction_detection_accuracy: number;
  missing_data_robustness: number;
  duplicate_detection_accuracy: number;
  average_matching_latency_ms: number;
  bob_extraction_validation_rate: number;
  total_eval_cases: number;
  ground_truth_matches: number;
  exact_match_cases: number;
  partial_match_cases: number;
  contradiction_cases: number;
  missing_data_cases: number;
  duplicate_am_cases: number;
  unmatched_cases: number;
}

export interface EvidenceGraphNode {
  id: string;
  label: string;
  sublabel?: string;
  type: string;
  group: string;
  result?: string;
  score?: number;
  weight?: number;
  notes?: string;
  contradiction?: boolean;
  source?: string;
  source_type?: string;
  image_id?: string;
  gemini_model?: string;
  sha256?: string;
  human_review_status?: string;
  timestamp?: string;
  provenance?: Record<string, any>;
  image_count?: number;
  details?: Record<string, any>;
}

export interface EvidenceGraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  type: string;
  status: string;
}

export interface EvidenceGraphData {
  match_id: string;
  match_score: number;
  evidence_quality: string;
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
  summary: string;
}

export interface CopilotMessage {
  id: string;
  sender: 'user' | 'bob';
  text: string;
  timestamp: string;
  tools_used?: Array<{ tool: string; parameters: Record<string, any>; result: any }>;
  suggested_actions?: string[];
}

export interface ClothingObservation {
  item_type?: string;
  color?: string;
  pattern?: string;
  description?: string;
  status: 'OBSERVED' | 'INFERRED' | 'UNKNOWN';
  confidence: number;
  notes?: string;
}

export interface JewelleryObservation {
  item_type?: string;
  material_or_color?: string;
  location?: string;
  description?: string;
  status: 'OBSERVED' | 'INFERRED' | 'UNKNOWN';
  confidence: number;
  notes?: string;
}

export interface TattooObservation {
  description?: string;
  location?: string;
  design_motifs?: string[];
  colors?: string[];
  status: 'OBSERVED' | 'INFERRED' | 'UNKNOWN';
  confidence: number;
  notes?: string;
}

export interface ScarObservation {
  description?: string;
  location?: string;
  mark_type?: string;
  status: 'OBSERVED' | 'INFERRED' | 'UNKNOWN';
  confidence: number;
  notes?: string;
}

export interface PhysicalCharacteristicObservation {
  attribute?: string;
  value?: string;
  status: 'OBSERVED' | 'INFERRED' | 'UNKNOWN';
  confidence: number;
  notes?: string;
}

export interface ImageQuality {
  status: 'GOOD' | 'FAIR' | 'POOR' | 'DEGRADED';
  occlusion: boolean;
  occlusion_details?: string;
  lighting?: string;
  resolution_assessment?: string;
}

export interface ImageExtractionObservations {
  clothing: ClothingObservation[];
  jewellery: JewelleryObservation[];
  tattoos: TattooObservation[];
  scars_or_marks: ScarObservation[];
  physical_characteristics: PhysicalCharacteristicObservation[];
  visible_text: string[];
  other_observations: string[];
}

export interface ImageExtractionPayload {
  record_type: 'AM' | 'PM';
  image_type: string;
  observations: ImageExtractionObservations;
  image_quality: ImageQuality;
  summary?: string;
  provenance?: Record<string, any>;
}

export interface ImageEvidence {
  id: string;
  incident_id: string;
  am_id?: string;
  pm_id?: string;
  storage_path: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  sha256: string;
  image_type: string;
  gemini_model: string;
  analysis_status: 'PENDING' | 'ANALYZING' | 'COMPLETED' | 'FAILED';
  extraction_json: ImageExtractionPayload;
  human_review_status: 'PENDING_REVIEW' | 'APPROVED' | 'MODIFIED_AND_APPROVED' | 'REJECTED';
  reviewed_by?: string;
  reviewed_at?: string;
  uploaded_by: string;
  uploaded_at: string;
  created_at: string;
  updated_at: string;
}

