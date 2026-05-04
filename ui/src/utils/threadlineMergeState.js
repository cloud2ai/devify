export function getThreadlineMergeState(threadline) {
  if (!threadline) {
    return 'original'
  }

  const isMergedSource = Boolean(threadline.merged_into_uuid)
  const hasMergedChildren = Boolean(threadline.has_merged_children)

  if (isMergedSource && hasMergedChildren) {
    return 'merged_again'
  }

  if (isMergedSource) {
    return 'merged_source'
  }

  if (hasMergedChildren) {
    return 'canonical'
  }

  return 'original'
}
