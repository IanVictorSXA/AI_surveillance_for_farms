import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { CameraGrid } from './components/CameraGrid';
import { AddCameraForm } from './components/AddCameraForm';
import { api } from './api';
import { Camera } from './types';
import { toast } from 'sonner';
import { Toaster } from 'sonner';

export default function App() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [isAddCameraOpen, setIsAddCameraOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadCameras();
  }, []);

  const loadCameras = async () => {
    setIsLoading(true);
    const fetchedCameras = await api.getCameras();
    setCameras(fetchedCameras);
    setIsLoading(false);
  };

  const handleAddCamera = async (location: string, streamUrl: string) => {
    const newCamera = await api.addCamera(location, streamUrl);
    if (newCamera) {
      setCameras([...cameras, newCamera]);
      toast.success('Camera added successfully', {
        description: `${location} is now being monitored`,
      });
    } else {
      toast.error('Failed to add camera', {
        description: 'Please check your Flask server is running',
      });
    }
  };

  const handleDeleteCamera = async (id: string) => {
    const camera = cameras.find(c => c.id === id);
    const success = await api.deleteCamera(id);
    if (success) {
      setCameras(cameras.filter(c => c.id !== id));
      toast.success('Camera removed', {
        description: camera ? `${camera.location} has been removed` : 'Camera removed',
      });
    } else {
      toast.error('Failed to remove camera');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-950 text-white">
      <Toaster position="top-right" theme="dark" />
      
      <Header 
        cameraCount={cameras.length}
        onOpenAddCamera={() => setIsAddCameraOpen(true)}
      />
      
      <div className="flex-1 overflow-hidden flex">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-400">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p>Loading cameras...</p>
            </div>
          </div>
        ) : (
          <CameraGrid cameras={cameras} onDeleteCamera={handleDeleteCamera} />
        )}
      </div>

      <AddCameraForm
        isOpen={isAddCameraOpen}
        onClose={() => setIsAddCameraOpen(false)}
        onAddCamera={handleAddCamera}
      />
    </div>
  );
}