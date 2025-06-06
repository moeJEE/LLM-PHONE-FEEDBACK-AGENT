/**
 * Helper functions for the application
 */

/**
 * Format a date to a human-readable string
 * @param {string|Date} date - Date to format
 * @param {boolean} includeTime - Whether to include time in the formatted string
 * @returns {string} Formatted date string
 */
export const formatDate = (date, includeTime = false) => {
  if (!date) return '';
  
  const dateObj = new Date(date);
  
  if (isNaN(dateObj.getTime())) {
    return ''; // Invalid date
  }
  
  const options = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  };
  
  if (includeTime) {
    options.hour = '2-digit';
    options.minute = '2-digit';
  }
  
  return dateObj.toLocaleDateString('en-US', options);
};

/**
 * Format a phone number to a human-readable string
 * @param {string} phoneNumber - Phone number to format
 * @returns {string} Formatted phone number
 */
export const formatPhoneNumber = (phoneNumber) => {
  if (!phoneNumber) return '';
  
  // Remove all non-digit characters
  const digitsOnly = phoneNumber.replace(/\D/g, '');
  
  // For US phone numbers
  if (digitsOnly.length === 10) {
    return `(${digitsOnly.slice(0, 3)}) ${digitsOnly.slice(3, 6)}-${digitsOnly.slice(6)}`;
  } else if (digitsOnly.length === 11 && digitsOnly[0] === '1') {
    return `+1 (${digitsOnly.slice(1, 4)}) ${digitsOnly.slice(4, 7)}-${digitsOnly.slice(7)}`;
  }
  
  // International or other format
  if (digitsOnly.length > 10) {
    return `+${digitsOnly.slice(0, digitsOnly.length - 10)} ${digitsOnly.slice(-10, -7)} ${digitsOnly.slice(-7, -4)}-${digitsOnly.slice(-4)}`;
  }
  
  // Return original if we can't format it
  return phoneNumber;
};

/**
 * Format a duration in seconds to a human-readable string
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration string (mm:ss)
 */
export const formatDuration = (seconds) => {
  if (seconds === null || seconds === undefined) return '';
  
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Truncate a string to a specified length
 * @param {string} str - String to truncate
 * @param {number} length - Maximum length
 * @param {string} ending - Ending to append if truncated
 * @returns {string} Truncated string
 */
export const truncateString = (str, length = 50, ending = '...') => {
  if (!str) return '';
  
  if (str.length > length) {
    return str.substring(0, length - ending.length) + ending;
  }
  
  return str;
};

/**
 * Extract a user-friendly error message
 * @param {Error|Object|string} error - Error object or message
 * @returns {string} User-friendly error message
 */
export const getErrorMessage = (error) => {
  if (!error) {
    return 'An unknown error occurred';
  }
  
  // If it's a string, return it directly
  if (typeof error === 'string') {
    return error;
  }
  
  // If it's an Error object
  if (error instanceof Error) {
    return error.message;
  }
  
  // If it's an API response error
  if (error.response && error.response.data) {
    const { data } = error.response;
    return data.message || data.error || 'An error occurred with the request';
  }
  
  // If it's a generic object with a message property
  if (error.message) {
    return error.message;
  }
  
  // Default fallback
  return 'An unexpected error occurred';
};

/**
 * Calculate the sentiment score label based on a numeric value
 * @param {number} score - Sentiment score (-1 to 1)
 * @returns {string} Sentiment label
 */
export const getSentimentLabel = (score) => {
  if (score === null || score === undefined) return 'Unknown';
  
  if (score >= 0.5) return 'Very Positive';
  if (score >= 0.1) return 'Positive';
  if (score > -0.1) return 'Neutral';
  if (score > -0.5) return 'Negative';
  return 'Very Negative';
};

/**
 * Get CSS class name for a sentiment score
 * @param {number} score - Sentiment score (-1 to 1)
 * @returns {string} CSS class name
 */
export const getSentimentClass = (score) => {
  if (score === null || score === undefined) return 'bg-gray-100 text-gray-800';
  
  if (score >= 0.5) return 'bg-green-100 text-green-800';
  if (score >= 0.1) return 'bg-green-50 text-green-600';
  if (score > -0.1) return 'bg-gray-100 text-gray-800';
  if (score > -0.5) return 'bg-red-50 text-red-600';
  return 'bg-red-100 text-red-800';
};

/**
 * Convert file size in bytes to human-readable format
 * @param {number} bytes - File size in bytes
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted file size
 */
export const formatFileSize = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Check if an object is empty
 * @param {Object} obj - Object to check
 * @returns {boolean} Whether the object is empty
 */
export const isEmptyObject = (obj) => {
  return obj && Object.keys(obj).length === 0 && obj.constructor === Object;
};

/**
 * Deep clone an object
 * @param {Object} obj - Object to clone
 * @returns {Object} Cloned object
 */
export const deepClone = (obj) => {
  return JSON.parse(JSON.stringify(obj));
};

/**
 * Check if a value is a valid URL
 * @param {string} value - Value to check
 * @returns {boolean} Whether the value is a valid URL
 */
export const isValidUrl = (value) => {
  try {
    new URL(value);
    return true;
  } catch (err) {
    return false;
  }
};

/**
 * Generate a random ID
 * @param {number} length - Length of the ID
 * @returns {string} Random ID
 */
export const generateId = (length = 8) => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  
  return result;
};