export function getThreadlineDisplayStatus(threadline) {
  if (!threadline) {
    return 'pending'
  }

  return threadline.status || 'pending'
}

export function isThreadlineProcessing(threadline) {
  return getThreadlineDisplayStatus(threadline) === 'processing'
}
