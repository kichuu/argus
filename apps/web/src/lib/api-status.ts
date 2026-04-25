import type { UseQueryResult } from "@tanstack/react-query";

export function apiStatus<T>(query: UseQueryResult<T>) {
  return {
    online: query.isSuccess && query.data != null,
    loading: query.isLoading,
  };
}
