// This file defines a FileUploadButton component that allows users to select and upload PDF files
// It includes a hidden file input and a button that triggers the file selection dialog
// The component handles file selection and calls the onFileSelect callback with the selected file

import React, { useRef, ChangeEvent } from 'react';
import { Paperclip, Loader2 } from 'lucide-react';

interface FileUploadButtonProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  uploading?: boolean;
}

export const FileUploadButton: React.FC<FileUploadButtonProps> = ({
  onFileSelect,
  disabled,
  uploading,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
      // Reset input value so the same file can be selected again
      e.target.value = '';
    }
  };

  return (
    <div className="relative">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf"
        className="hidden"
        disabled={disabled || uploading}
      />
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || uploading}
        className="p-3 rounded-full hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 disabled:opacity-40 disabled:hover:bg-transparent transition-colors flex items-center justify-center cursor-pointer"
        title="Upload PDF document"
      >
        {uploading ? (
          <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
        ) : (
          <Paperclip className="w-5 h-5" />
        )}
      </button>
    </div>
  );
};
