import { Camera, Plus } from 'lucide-react';
import logo from '../../assets/6bdd912a4b9e5c34f6f38dc64adc0b09d284cebd.png';

interface HeaderProps {
  cameraCount: number;
  onOpenAddCamera: () => void;
}

export function Header({ cameraCount, onOpenAddCamera }: HeaderProps) {
  return (
    <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <img src={logo} alt="Logo" className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Dark Knight</h1>
              <p className="text-sm text-gray-400">Local Camera Surveillance System</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-800 rounded-lg">
            <Camera className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-300">
              <span className="font-semibold text-white">{cameraCount}</span> Camera{cameraCount !== 1 ? 's' : ''}
            </span>
          </div>
          
          <button
            onClick={onOpenAddCamera}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Camera
          </button>
        </div>
      </div>
    </header>
  );
}