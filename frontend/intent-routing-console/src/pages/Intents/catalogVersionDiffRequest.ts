export type CatalogVersionDiffRequestSnapshot = {
  requestId: number;
  serviceId: string;
};

export const nextCatalogVersionDiffRequestId = (currentRequestId: number) =>
  currentRequestId + 1;

export const canApplyCatalogVersionDiffResult = (
  snapshot: CatalogVersionDiffRequestSnapshot,
  current: CatalogVersionDiffRequestSnapshot,
) =>
  snapshot.requestId === current.requestId &&
  snapshot.serviceId === current.serviceId;
