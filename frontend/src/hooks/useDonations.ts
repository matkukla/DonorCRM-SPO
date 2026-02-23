// Backward compatibility -- re-export Gift hooks as Donation names
// This file will be removed once all consumers are migrated
export {
  useGifts as useDonations,
  useGift as useDonation,
  useCreateGift as useCreateDonation,
  useUpdateGift as useUpdateDonation,
  useDeleteGift as useDeleteDonation,
} from "./useGifts"
