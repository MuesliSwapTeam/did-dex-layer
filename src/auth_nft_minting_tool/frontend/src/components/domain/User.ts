export enum AccessLevel {
  NONE = 0,
  LOW = 1,
  MEDIUM = 2,
  HIGH = 3
}

export interface User {
  did: string;
  accessLevel: AccessLevel;
}
