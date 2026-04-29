import React, { useEffect, useMemo, useState } from 'react';
import './TransformationShowcase.css';

const transformationImagesContext = require.context('../assets/transformations', false, /\.(png|jpe?g|webp)$/i);

const transformationImages = transformationImagesContext.keys()
  .map((key) => {
    const src = transformationImagesContext(key);
    const fileName = key.replace('./', '');
    const numericOrder = Number.parseInt(fileName, 10);
    return {
      src,
      fileName,
      order: Number.isNaN(numericOrder) ? 999 : numericOrder,
    };
  })
  .sort((a, b) => a.order - b.order || a.fileName.localeCompare(b.fileName));

function TransformationShowcase({ compact = false }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const images = useMemo(() => transformationImages, []);

  useEffect(() => {
    if (images.length <= 1) return undefined;
    const timer = setInterval(() => {
      setActiveIndex((current) => (current + 1) % images.length);
    }, compact ? 2600 : 3600);
    return () => clearInterval(timer);
  }, [compact, images.length]);

  if (!images.length) return null;

  const activeImage = images[activeIndex];
  const previewImages = compact ? images.slice(0, 8) : images;
  const previousIndex = (activeIndex - 1 + images.length) % images.length;
  const nextIndex = (activeIndex + 1) % images.length;

  return (
    <section className={`transformation-showcase ${compact ? 'is-compact' : ''}`} aria-label="Client transformations">
      <div className="transformation-copy">
        <p className="transformation-kicker">Client Transformations</p>
        <h2>Real before-and-after results from the program</h2>
        <p>
          These are past client transformations from people who followed the coaching and meal-planning process.
        </p>
      </div>

      <div className="transformation-stage">
        <button
          type="button"
          className="transformation-nav"
          onClick={() => setActiveIndex(previousIndex)}
          aria-label="Previous transformation"
        >
          &lsaquo;
        </button>
        <div className="transformation-frame">
          <img
            src={activeImage.src}
            alt={`Client transformation ${activeImage.order}`}
            className="transformation-main-image"
          />
        </div>
        <button
          type="button"
          className="transformation-nav"
          onClick={() => setActiveIndex(nextIndex)}
          aria-label="Next transformation"
        >
          &rsaquo;
        </button>
      </div>

      <div className="transformation-strip" aria-label="Transformation gallery thumbnails">
        {previewImages.map((image, index) => (
          <button
            type="button"
            key={image.fileName}
            className={`transformation-thumb ${activeIndex === index ? 'is-active' : ''}`}
            onClick={() => setActiveIndex(index)}
            aria-label={`View transformation ${image.order}`}
          >
            <img src={image.src} alt="" aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
  );
}

export default TransformationShowcase;
