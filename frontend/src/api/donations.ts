// Backward compatibility -- re-export Gift types as Donation names
// This file will be removed once all consumers are migrated
export {
  getGifts as getDonations,
  getGift as getDonation,
  createGift as createDonation,
  updateGift as updateDonation,
  deleteGift as deleteDonation,
} from "./gifts"
export type {
  Gift as Donation,
  GiftCreate as DonationCreate,
  GiftUpdate as DonationUpdate,
} from "./gifts"
