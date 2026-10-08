/** The Worker's cron schedules (`wrangler.jsonc` → triggers.crons). A separate
 * module: the Worker's entry may export only handlers and classes. */

/** Every permanent account's log leaves Cloudflare once a day, in the small
 *  hours in Tallinn (`LearnerState.backup`). Any other schedule is reminders. */
export const BACKUP_CRON = "37 1 * * *";
