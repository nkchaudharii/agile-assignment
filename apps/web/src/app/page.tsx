'use client';

import { useState } from 'react';
import MediaSelectionButton from "@/components/MediaSelectionButton";
import CopyTextButton from "@/components/CopyTextButton";

export default function Home() {
  const [isDragging, setIsDragging] = useState(false);
  const [dragCounter, setDragCounter] = useState(0);

  const handleDragEnter = (e: any) => {
    e.preventDefault();
    setDragCounter(prev => prev + 1);
    if (dragCounter === 0) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: any) => {
    e.preventDefault();
    setDragCounter(prev => prev - 1);
    if (dragCounter - 1 === 0) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e: any) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    setDragCounter(0);

    const files: File[] = Array.from(e.dataTransfer.files);
    
    const validTypes = [
      'application/pdf',
      'text/plain',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/webp',
      'image/bmp',
      'image/tiff'
    ];
    const invalidFiles = files.filter((file: File) => !validTypes.includes(file.type));
    
    if (invalidFiles.length > 0) {
      alert(`Some files are not valid. Valid formats: docx, pdf, txt, img. Invalid files: ${invalidFiles.map((f: File) => f.name).join(', ')}`);
    } else {
      alert('Files dropped successfully');
    }
  };

  return (
    <main
      style={{
        minHeight: '100vh',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'system-ui, sans-serif',
        padding: '24px',
        backgroundColor: '#f8fafc',
        gap: '20px'
      }}
    >
      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        style={{
          width: '360px',
          padding: '28px',
          borderRadius: '18px',
          border: '2px dashed #64748b',
          backgroundColor: '#ffffff',
          boxShadow: '0 18px 40px rgba(15, 23, 42, 0.08)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px',
          textAlign: 'center',
          position: 'relative'
        }}
      >
        <h1 style={{ margin: 0, fontSize: '1.25rem', color: '#0f172a' }}>
          Drag files here
        </h1>
        <p style={{ margin: 0, color: '#475569' }}>
          Valid formats: docx, pdf, txt, jpg, png, gif, webp, bmp, tiff.
        </p>
        <p style={{ margin: 0, fontSize: '0.95rem', color: '#64748b' }}>
          Drop files on the box above to upload.
        </p>
        {isDragging && (
          <div style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '18px',
            backgroundColor: 'rgba(99, 102, 241, 0.14)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#0f172a',
            fontSize: '1rem',
            pointerEvents: 'none'
          }}>
            Drop files now
          </div>
        )}
      </div>

      <div style={{ width: "100%", maxWidth: "700px", display: "flex", justifyContent: "center" }}>
        
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "12px 16px",
            border: "1.5px solid #e5e7eb",
            borderRadius: "999px",
            width: "fit-content",
            background: "#fff",
            boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
          }}
        >
          <MediaSelectionButton />
        </div>
      </div>
      <div style={{ 
        width: "100%", 
        maxWidth: "250px", 
        marginTop: "2px",
        display: "flex",
        justifyContent: "center"
      }}>
        <button
          onClick={() => {
            navigator.clipboard.writeText("LLM OUTPUT DATA");
            alert("LLM Output copied to clipboard!");
          }}
          style={{
            width: "100%",
            padding: "8px",
            backgroundColor: "#6862e2",
            color: "white",
            border: "none",
            borderRadius: "12px",
            fontWeight: "bold",
            fontSize: "0.9rem",
            cursor: "pointer",
            boxShadow: "0 4px 12px rgba(79, 70, 229, 0.2)",
            transition: "transform 0.1s active"
          }}
        >
          CLICK TO COPY LLM OUTPUT
        </button>
      </div>
    </main>
  );
}