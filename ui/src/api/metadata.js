import api from './index'

// Update one or more metadata fields for a threadline using partial update
// Payload should only include the keys that need to be created or updated
export const metadataApi = {
  async patchThreadlineMetadata(id, payload) {
    const response = await api.patch(`/v1/threadlines/${id}/metadata`, payload)
    return response.data
  }
}
