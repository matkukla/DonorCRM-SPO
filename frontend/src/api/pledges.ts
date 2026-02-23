// Backward compatibility -- re-export RecurringGift types as Pledge names
export {
  getRecurringGifts as getPledges,
  getRecurringGift as getPledge,
  createRecurringGift as createPledge,
  updateRecurringGift as updatePledge,
  deleteRecurringGift as deletePledge,
} from "./gifts"

export type {
  RecurringGift as Pledge,
  RecurringGiftCreate as PledgeCreate,
  RecurringGiftUpdate as PledgeUpdate,
  RecurringGiftStatus as PledgeStatus,
  RecurringGiftFrequency as PledgeFrequency,
} from "./gifts"

export {
  recurringGiftStatusLabels as pledgeStatusLabels,
  recurringGiftFrequencyLabels as pledgeFrequencyLabels,
} from "./gifts"
