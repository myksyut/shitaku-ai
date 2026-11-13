export function hasOccurrenceStarted(startAt: string) {
  return new Date(startAt).getTime() <= Date.now()
}
