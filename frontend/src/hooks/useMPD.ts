import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  uploadMPDFile,
  getMPDOverview,
  getMPDMyData,
  getMPDUploadHistory,
} from "@/api/mpd"

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
export function useMPDOverview() {
  return useQuery({
    queryKey: ["mpd", "overview"],
    queryFn: getMPDOverview,
  })
}

/**
 * Fetch current user's own MPD snapshot
 */
export function useMPDMyData() {
  return useQuery({
    queryKey: ["mpd", "me"],
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
