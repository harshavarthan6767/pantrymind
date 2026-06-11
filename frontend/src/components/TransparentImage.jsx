import React, { useEffect, useRef, useState } from 'react';

const TransparentImage = ({ src, alt, className }) => {
  const canvasRef = useRef(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!src) return;
    
    // Reset state on src change
    setLoaded(false);
    setError(false);

    const img = new Image();
    img.crossOrigin = 'Anonymous';
    img.src = src;

    img.onload = () => {
      try {
        const canvas = canvasRef.current;
        if (!canvas) return;

        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(img, 0, 0);

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;
        const w = canvas.width;
        const h = canvas.height;

        // Tolerance for "white"
        const threshold = 235;
        
        const isWhite = (idx) => {
          // Also check if alpha is already 0
          if (data[idx + 3] === 0) return true;
          return data[idx] >= threshold && data[idx + 1] >= threshold && data[idx + 2] >= threshold;
        };

        const visited = new Uint8Array(w * h);
        
        // Pre-allocate queue for speed (max possible is w*h)
        const qx = new Int32Array(w * h);
        const qy = new Int32Array(w * h);
        let head = 0;
        let tail = 0;

        // Start from edges
        const starts = [
          [0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1],
          [Math.floor(w/2), 0], [Math.floor(w/2), h - 1], 
          [0, Math.floor(h/2)], [w - 1, Math.floor(h/2)]
        ];

        for (const [sx, sy] of starts) {
          const pos = sy * w + sx;
          const sIdx = pos * 4;
          if (isWhite(sIdx) && !visited[pos]) {
            qx[tail] = sx;
            qy[tail] = sy;
            tail++;
            visited[pos] = 1;
          }
        }

        while (head < tail) {
          const x = qx[head];
          const y = qy[head];
          head++;
          
          const idx = (y * w + x) * 4;

          // Make transparent
          data[idx + 3] = 0;

          // Check 4 neighbors
          // Left
          if (x > 0) {
              const nPos = y * w + (x - 1);
              if (!visited[nPos]) {
                  visited[nPos] = 1;
                  if (isWhite(nPos * 4)) {
                      qx[tail] = x - 1; qy[tail] = y; tail++;
                  }
              }
          }
          // Right
          if (x < w - 1) {
              const nPos = y * w + (x + 1);
              if (!visited[nPos]) {
                  visited[nPos] = 1;
                  if (isWhite(nPos * 4)) {
                      qx[tail] = x + 1; qy[tail] = y; tail++;
                  }
              }
          }
          // Top
          if (y > 0) {
              const nPos = (y - 1) * w + x;
              if (!visited[nPos]) {
                  visited[nPos] = 1;
                  if (isWhite(nPos * 4)) {
                      qx[tail] = x; qy[tail] = y - 1; tail++;
                  }
              }
          }
          // Bottom
          if (y < h - 1) {
              const nPos = (y + 1) * w + x;
              if (!visited[nPos]) {
                  visited[nPos] = 1;
                  if (isWhite(nPos * 4)) {
                      qx[tail] = x; qy[tail] = y + 1; tail++;
                  }
              }
          }
        }

        ctx.putImageData(imageData, 0, 0);
        setLoaded(true);
      } catch (err) {
        console.error("Canvas processing failed:", err);
        setError(true);
      }
    };
    
    img.onerror = () => {
      console.warn("TransparentImage failed to load with CORS, falling back to standard img");
      setError(true);
    };
  }, [src]);

  if (error) {
    return <img src={src} alt={alt} className={className} />;
  }

  return (
    <canvas 
      ref={canvasRef} 
      className={className} 
      style={{ opacity: loaded ? 1 : 0, transition: 'opacity 0.3s ease' }}
      aria-label={alt}
    />
  );
};

export default TransparentImage;
