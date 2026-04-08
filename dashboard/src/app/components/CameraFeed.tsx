import { useState, useEffect, useRef } from 'react';
import { Trash2, Signal, SignalZero, Maximize2 } from 'lucide-react';
import { Camera } from '../types';

interface CameraFeedProps {
  camera: Camera;
  onDelete: (id: string) => void;
}

export function CameraFeed({ camera, onDelete }: CameraFeedProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [showControls, setShowControls] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    // Simulate connection status
    const timer = setTimeout(() => setIsConnected(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  const handleFullscreen = () => {
    if (imgRef.current && imgRef.current.requestFullscreen) {
      imgRef.current.requestFullscreen();
    }
  };

  return (
    <div 
      className="relative bg-gray-900 rounded-lg overflow-hidden aspect-video border border-gray-700"
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      {/* Camera Feed */}
      <div className="w-full h-full flex items-center justify-center bg-gray-800">
        <img
          ref={imgRef}
          src={`http://${window.location.hostname}:5000/video_feed/${camera.id}`}
          alt={camera.location}
          className="w-full h-full object-cover"
          onError={() => setIsConnected(false)}
          onLoad={() => setIsConnected(true)}
        />
        
        {/* Loading/No Signal State */}
        {!isConnected && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
            <div className="text-center text-gray-500">
              <SignalZero className="w-12 h-12 mx-auto mb-2" />
              <p className="text-sm">Connecting...</p>
            </div>
          </div>
        )}
      </div>

      {/* Camera Info Overlay */}
      <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/70 to-transparent p-3">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-white">{camera.location}</h3>
            <p className="text-xs text-gray-300 mt-1">{camera.streamUrl}</p>
          </div>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Signal className="w-4 h-4 text-green-500" />
            ) : (
              <SignalZero className="w-4 h-4 text-red-500" />
            )}
          </div>
        </div>
      </div>

      {/* Controls Overlay */}
      {showControls && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3">
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={handleFullscreen}
              className="p-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
              title="Fullscreen"
            >
              <Maximize2 className="w-4 h-4 text-white" />
            </button>
            <button
              onClick={() => onDelete(camera.id)}
              className="p-2 bg-red-500/80 hover:bg-red-500 rounded-lg transition-colors"
              title="Delete Camera"
            >
              <Trash2 className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>
      )}

      {/* Timestamp */}
      <div className="absolute top-3 right-3 bg-black/50 px-2 py-1 rounded text-xs text-white font-mono">
        {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
}
