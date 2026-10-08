export interface ApiResponse<T> {
  data: T;
}

export interface ApiListResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ApiMessageResponse {
  message: string;
}

export interface ApiErrorResponse {
  error: string;
}
