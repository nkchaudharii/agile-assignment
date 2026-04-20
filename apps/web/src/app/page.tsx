"use client";
import MediaSelectionButton from "@/components/MediaSelectionButton";

export default function Home() {
  return (
    <main style={{ 
      display: "flex", 
      justifyContent: "center", 
      alignItems: "flex-end", 
      height: "100vh", 
      padding: "2rem",
      background: "#f9fafb"
    }}>
      <div style={{ width: "100%", maxWidth: "700px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "12px 16px",
            border: "1.5px solid #e5e7eb",
            borderRadius: "999px",
            width: "100%",
            background: "#fff",
            boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
          }}
        >
          <MediaSelectionButton />
        </div>
      </div>
    </main>
  );
}
