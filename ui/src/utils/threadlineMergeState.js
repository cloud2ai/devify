export function getThreadlineMergeState(threadline) {
  if (!threadline) {
    return 'original'
  }

  const hasMergedChildren = Boolean(threadline.has_merged_children)

  if (hasMergedChildren) {
    return 'canonical'
  }

  return 'original'
}
