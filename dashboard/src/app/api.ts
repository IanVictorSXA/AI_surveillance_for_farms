import { Camera } from './types';

const API_BASE_URL = `http://${window.location.hostname}:5000`;

export const api = {
  // Fetch all cameras
  async getCameras(): Promise<Camera[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/cameras`);
      if (!response.ok) throw new Error('Failed to fetch cameras');
      return await response.json();
    } catch (error) {
      // Silently fail if Flask server is not running
      // This is expected on first load before the backend is started
      return [];
    }
  },

  // Add a new camera
  async addCamera(location: string, streamUrl: string): Promise<Camera | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/cameras`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ location, streamUrl }),
      });
      if (!response.ok) throw new Error('Failed to add camera');
      return await response.json();
    } catch (error) {
      // Error will be handled by the UI toast notification
      return null;
    }
  },

  // Delete a camera
  async deleteCamera(id: string): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/cameras/${id}`, {
        method: 'DELETE',
      });
      return response.ok;
    } catch (error) {
      // Error will be handled by the UI toast notification
      return false;
    }
  },
};