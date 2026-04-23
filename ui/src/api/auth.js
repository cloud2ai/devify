import api from './index'

export const authApi = {
  // Login with username and password
  login(credentials) {
    return api.post('/v1/auth/login', credentials)
  },

  // Get user profile
  getProfile() {
    return api.get('/v1/auth/user')
  },

  // Update user profile
  updateProfile(profileData) {
    return api.patch('/v1/auth/user', profileData)
  },

  // Logout
  logout() {
    return api.post('/v1/auth/logout')
  },

  // Refresh token
  refreshToken(refreshToken) {
    return api.post('/v1/auth/token/refresh', {
      refresh: refreshToken
    })
  },

  // Register (for future use)
  register(userData) {
    return api.post('/v1/auth/registration', userData)
  },

  // Reset password - Send reset email
  resetPassword(email) {
    return api.post('/v1/auth/password/reset', { email })
  },

  // Confirm password reset with uid and token
  confirmPasswordReset(data) {
    return api.post('/v1/auth/password/reset/confirm', data)
  },

  // Change password (requires authentication)
  changePassword(passwordData) {
    return api.post('/v1/auth/password/change', passwordData)
  },

  // Send registration email
  sendRegistrationEmail(data) {
    return api.post('/v1/auth/register/send-email', data)
  },

  // Verify registration token
  verifyRegistrationToken(token) {
    return api.get(`/v1/auth/register/verify-token/${token}`)
  },

  // Complete registration
  completeRegistration(data) {
    return api.post('/v1/auth/register/complete', data)
  },

  // Complete OAuth setup (Google, WeChat, etc.)
  completeOAuthSetup(data) {
    return api.post('/v1/auth/oauth/complete-setup', data)
  },

  // Backward compatibility alias
  completeGoogleSetup(data) {
    return this.completeOAuthSetup(data)
  },

  // Check username availability
  checkUsernameAvailability(username) {
    return api.get(`/v1/auth/check-username/${username}`)
  },

  // Get available scenes
  getAvailableScenes(language) {
    return api.get('/v1/auth/scenes', {
      params: { language }
    })
  }
}

// Export individual functions for easier imports
export const {
  login,
  getProfile,
  updateProfile,
  logout,
  refreshToken,
  register,
  resetPassword,
  confirmPasswordReset,
  changePassword,
  sendRegistrationEmail,
  verifyRegistrationToken,
  completeRegistration,
  completeOAuthSetup,
  completeGoogleSetup,
  checkUsernameAvailability,
  getAvailableScenes
} = authApi
