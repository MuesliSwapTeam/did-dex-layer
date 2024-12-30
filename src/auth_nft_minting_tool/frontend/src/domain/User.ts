export enum AccessLevel {
  NONE = 0,
  LOW = 1,
  MEDIUM = 2,
  HIGH = 3
}

export interface User {
  atala_did: string;
  challenge: string;
  challenge_timestamp: string;
  connect_did: string;
  access_level: AccessLevel;
}
