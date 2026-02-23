// Backward compatibility -- re-export RecurringGift hooks as Pledge names
export {
  useRecurringGifts as usePledges,
  useRecurringGift as usePledge,
  useCreateRecurringGift as useCreatePledge,
  useUpdateRecurringGift as useUpdatePledge,
  useDeleteRecurringGift as useDeletePledge,
} from "./useGifts"
