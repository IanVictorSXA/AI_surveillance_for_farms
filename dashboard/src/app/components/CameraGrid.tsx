import { Camera } from '../types';
import { CameraFeed } from './CameraFeed';

interface CameraGridProps {
  cameras: Camera[];
  onDeleteCamera: (id: string) => void;
}

export function CameraGrid({ cameras, onDeleteCamera }: CameraGridProps) {
  if (cameras.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl mb-2">No cameras added yet</p>
          <p className="text-sm">Use the "Add Camera" form to add your first camera</p>
        </div>
      </div>
    );
  }

  const getGridClass = () => {
    if (cameras.length === 1) return 'grid-cols-1';
    if (cameras.length === 2) return 'grid-cols-2';
    if (cameras.length <= 4) return 'grid-cols-2';
    if (cameras.length <= 6) return 'grid-cols-3';
    return 'grid-cols-4';
  };

  return (
    <div className={`grid ${getGridClass()} gap-4 flex-1 min-h-0 p-6 overflow-y-auto`}>
      {cameras.map((camera) => (
        <CameraFeed
          key={camera.id}
          camera={camera}
          onDelete={onDeleteCamera}
        />
      ))}
    </div>
  );
}
