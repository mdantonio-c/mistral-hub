export interface CustomUser {
  disk_quota: number;
  /**
   * @nullable
   */
  amqp_queue: string;
  requests_expiration_days: number;
}
