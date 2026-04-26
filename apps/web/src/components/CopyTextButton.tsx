"use client";

import { useState } from "react";

interface CopyButtonProps {
  textToCopy: string;
}

export default function CopyTextButton({ textToCopy }: CopyButtonProps) {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`px-3 py-1 text-sm font-medium rounded-md border transition-all duration-200 
        ${isCopied 
          ? "bg-green-100 text-green-700 border-green-500" 
          : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50 active:bg-gray-100 shadow-sm"
        }`}
    >
      {isCopied ? "✓ Copied" : "Copy"}
    </button>
  );
}