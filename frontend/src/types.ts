export type AppRole = "Student" | "Staff Sekretariat";
export type ReservationStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED" | "COMPLETED";
export type RoomStatus = "ACTIVE" | "INACTIVE" | "MAINTENANCE";

export interface AuthUser {
  id: string; name: string; email: string; student_identifier: string | null;
  phone: string | null; profile_image_url: string | null; role: AppRole;
  account_status: "ACTIVE" | "DISABLED"; created_at: string;
}
export interface TokenResponse { access_token: string; token_type: string; expires_in: number; user: AuthUser; }
export interface Room {
  id: string; room_name: string; room_code: string | null; building: string; faculty: string | null;
  floor: string | null; location_description: string | null; capacity: number; capacity_estimate?: string | null; description: string | null; facilities: string[];
  operating_hours: Record<string, Array<{ start: string; end: string }>>;
  room_status: RoomStatus; photo_url: string | null; created_at?: string; updated_at?: string;
}
export interface Reservation {
  id: string; user_id: string; room_id: string; purpose: string; reservation_date: string;
  start_time: string; end_time: string; participant_count: number; notes: string | null;
  status: ReservationStatus; admin_id: string | null; rejection_reason: string | null;
  submitted_at: string; approved_at: string | null; cancelled_at: string | null;
  cancellation_reason: string | null;
  room?: Pick<Room, "id" | "room_name" | "building" | "capacity" | "photo_url">;
  applicant?: { id: string; name: string; email: string };
}
export interface AvailabilityResult { room_id: string; available: boolean; reasons: string[]; checked_at: string; }
export interface AppNotification {
  id: string; notification_type: string; title: string; message: string; read_at: string | null;
  delivery_status: string; email_delivery_status: string; email_sent_at: string | null; created_at: string;
}
export interface DashboardSummary {
  role: string; total_rooms?: number; active_rooms?: number; total_users?: number;
  total_reservations: number; pending: number; approved: number; rejected: number; cancelled: number; completed: number;
}
export interface Schedule {
  id: string; room_id: string; course_name: string; schedule_date: string | null; day_of_week: number | null;
  start_time: string; end_time: string; schedule_status: string; data_source: string; last_updated_at: string;
}
export interface RoomUnavailability { id: string; room_id: string; unavailable_date: string; start_time: string; end_time: string; reason: string; is_active: boolean; }
export interface PageMeta { page: number; limit: number; total: number; total_pages: number; }
export interface PageResult<T> { items: T[]; meta?: PageMeta; }

export interface AlternativeSlotSearch {
  date: string;
  duration_minutes: number;
  participant_count: number;
  room_id?: string | null;
  faculty?: string | null;
  building?: string | null;
  facilities?: string[];
  preferred_start_time?: string | null;
  search_days?: number;
  slot_step_minutes?: number;
  limit?: number;
}
export interface AlternativeSlot {
  room: Room;
  date: string;
  start_time: string;
  end_time: string;
  participant_count: number;
  duration_minutes: number;
  match_reasons: string[];
  availability_source: string;
}
export interface AlternativeSlotsResult {
  items: AlternativeSlot[];
  criteria: {
    requested_date: string;
    duration_minutes: number;
    participant_count: number;
    search_days: number;
    slot_step_minutes: number;
  };
  availability_note: string;
}
export interface AssistantContextMessage {
  role: "user" | "assistant";
  content: string;
}
export interface AssistantChatRequest {
  message: string;
  /** Opaque ID for the authenticated student's short-lived conversation state. */
  conversation_id?: string | null;
  /** Up to ten previous turns from this browser tab; not persisted as raw chat by the API. */
  context?: AssistantContextMessage[];
  faculty?: string | null;
  building?: string | null;
  min_capacity?: number | null;
  facilities?: string[];
  date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  participant_count?: number;
}
export type AssistantFeedbackReason =
  | "TOO_FORMAL"
  | "TOO_LONG"
  | "TOO_SHORT"
  | "WRONG_INTENT"
  | "WRONG_NORMALIZATION"
  | "RESULTS_NOT_RELEVANT"
  | "OTHER";
export interface AssistantFeedbackRequest {
  intent: string;
  rating: "HELPFUL" | "NOT_HELPFUL";
  reason_code?: AssistantFeedbackReason;
}
export interface AssistantChatSlots {
  faculty: string | null;
  building: string | null;
  min_capacity: number | null;
  facilities: string[];
  date: string | null;
  start_time: string | null;
  end_time: string | null;
  participant_count: number;
  search_terms: string[];
}
export interface AssistantReservationSummary {
  id: string;
  room_name: string;
  building: string;
  date: string;
  start_time: string;
  end_time: string;
  participant_count: number;
  status: ReservationStatus;
  purpose: string;
}
export type AssistantResultType = "ROOMS_FOUND" | "ALTERNATIVE_SLOTS" | "RESERVATIONS_FOUND" | "ROOM_DETAILS" | "NO_RESULTS";
export interface AssistantChatResult {
  /** Structured fields are optional so the client remains compatible with an older API deployment. */
  assistant_name?: string;
  conversation_id?: string | null;
  slots?: AssistantChatSlots;
  confidence?: number | null;
  confidence_basis?: "RULE_HEURISTIC" | "AI_FALLBACK" | null;
  missing_fields?: string[];
  requires_clarification?: boolean;
  clarification_message?: string | null;
  result_type?: AssistantResultType;
  requires_confirmation?: boolean;
  data?: {
    rooms: Room[];
    alternative_slots: AlternativeSlot[];
    reservations?: AssistantReservationSummary[];
    filters: AssistantChatSlots;
  };
  engine: string;
  intent: string;
  message: string;
  filters: {
    faculty: string | null;
    building: string | null;
    min_capacity: number | null;
    facilities: string[];
    date: string | null;
    start_time: string | null;
    end_time: string | null;
    participant_count: number;
  };
  rooms: Room[];
  alternative_slots: AlternativeSlot[];
  follow_up_questions: string[];
  reservation_action: string;
  privacy: string;
}
