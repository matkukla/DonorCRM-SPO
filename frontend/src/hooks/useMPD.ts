import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  uploadMPDFile,
  getMPDOverview,
  getMPDMyData,
  getMPDUploadHistory,
} from "@/api/mpd"
import { useViewAs } from "@/providers/ViewAsProvider"

/**
 * Upload an MPD Smartsheet file (CSV or XLSX)
 * Invalidates all MPD queries on success to refresh overview/my-data/uploads
 */
export function useMPDUpload() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => uploadMPDFile(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mpd"] })
    },
  })
}

/**
 * Fetch per-missionary latest MPD data (admin only)
 */
export function useMPDOverview({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["mpd", "overview"],
    queryFn: getMPDOverview,
    enabled,
  })
}

/**
 * Fetch the "my data" MPD snapshot for the active user. In View-As mode the
 * X-View-As-User-Id header makes the API return the viewed user's snapshot,
 * so we bake `viewAsUserId` into the queryKey to prevent cache collisions.
 */
export function useMPDMyData() {
  const { viewAsUserId } = useViewAs()
  return useQuery({
    queryKey: ["mpd", "me", viewAsUserId ?? "self"],
    queryFn: getMPDMyData,
  })
}

/**
 * Fetch MPD upload history (admin only)
 */
export function useMPDUploadHistory() {
  return useQuery({
    queryKey: ["mpd", "uploads"],
    queryFn: getMPDUploadHistory,
  })
}
