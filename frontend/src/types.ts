export type AppRole = "Student" | "TU/Admin";
export type ReservationStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED" | "COMPLETED";
export type RoomStatus = "ACTIVE" | "INACTIVE" | "MAINTENANCE";

export interface AuthUser {
  id: string; name: string; email: string; student_identifier: string | null;
  phone: string | null; profile_image_url: string | null; role: AppRole;
  account_status: "ACTIVE" | "DISABLED"; created_at: string;
}
export interface TokenResponse { access_token: string; token_type: string; expires_in: number; user: AuthUser; }
export interface Room {
  id: string; room_name: string; room_code: string | null; building: string; floor: string | null;
  capacity: number; description: string | null; facilities: string[];
  operating_hours: Record<string, Array<{ start: string; end: string }>>;
  room_status: RoomStatus; photo_url: string | null; created_at?: string; updated_at?: string;
}
export interface Reservation {
  id: string; user_id: string; room_id: string; purpose: string; reservation_date: string;
  start_time: string; end_time: string; participant_count: number; notes: string | null;
  status: ReservationStatus; admin_id: string | null; rejection_reason: string | null;
  submitted_at: string; approved_at: string | null; cancelled_at: string | null;
  cancellation_reason: string | null;
  room?: Pick<Room, "id" | "room_name" | "building" | "capacity">;
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
export interface PageMeta { page: number; limit: number; total: number; total_pages: number; }
export interface PageResult<T> { items: T[]; meta?: PageMeta; }