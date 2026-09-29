(function () {
  const ready = callback => document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', callback)
    : callback();

  ready(async () => {
    try {
      const response = await fetch('photos/manifest.json', { cache: 'no-cache' });
      if (!response.ok) return;

      const data = await response.json();
      const images = Array.isArray(data.images) ? data.images : Array.isArray(data) ? data : [];
      if (!images.length) return;

      const sourceFor = image => image && (image.full || image.thumb);
      const thumbFor = image => image && (image.thumb || image.full);

      const heroImage = document.querySelector('.hero-banner__img');
      if (heroImage) {
        const hero = images.find(image => image.id === '001') || images[0];
        heroImage.addEventListener('load', () => heroImage.classList.add('is-ready'), { once: true });
        heroImage.src = sourceFor(hero);
      }

      function applyCovers() {
        document.querySelectorAll('[data-photo-slot^="card-"]').forEach((element, index) => {
          const image = images[(17 + index * 19) % images.length];
          element.style.backgroundImage = `url("${thumbFor(image)}")`;
        });
      }

      document.addEventListener('photos:refresh', applyCovers);
      applyCovers();

      const strip = document.querySelector('[data-photo-strip]');
      if (!strip) return;

      const count = Math.min(12, images.length);
      const selection = Array.from({ length: count }, (_, index) => images[(index * 9) % images.length]);
      let currentIndex = -1;
      let previousFocus = null;

      const lightbox = document.createElement('div');
      lightbox.className = 'lightbox';
      lightbox.id = 'lightbox';
      lightbox.setAttribute('role', 'dialog');
      lightbox.setAttribute('aria-modal', 'true');
      lightbox.setAttribute('aria-label', 'Expanded field photograph');
      lightbox.setAttribute('aria-hidden', 'true');
      lightbox.innerHTML = `
        <button class="lightbox-close" type="button" aria-label="Close photograph">&times;</button>
        <img class="lightbox-img" alt="">
      `;
      document.body.appendChild(lightbox);

      const lightboxImage = lightbox.querySelector('.lightbox-img');
      const closeButton = lightbox.querySelector('.lightbox-close');

      function show(index) {
        currentIndex = index;
        const image = selection[currentIndex];
        lightboxImage.src = sourceFor(image);
        lightboxImage.alt = image.alt || 'Expanded field photograph';
        lightbox.classList.add('is-visible');
        lightbox.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        closeButton.focus();
      }

      function close() {
        lightbox.classList.remove('is-visible');
        lightbox.setAttribute('aria-hidden', 'true');
        lightboxImage.src = '';
        document.body.style.overflow = '';
        currentIndex = -1;
        if (previousFocus) previousFocus.focus();
      }

      function move(delta) {
        if (currentIndex < 0) return;
        currentIndex = (currentIndex + delta + selection.length) % selection.length;
        const image = selection[currentIndex];
        lightboxImage.src = sourceFor(image);
        lightboxImage.alt = image.alt || 'Expanded field photograph';
      }

      selection.forEach((image, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.setAttribute('aria-label', `Open photograph ${index + 1} of ${selection.length}`);

        const thumbnail = new Image();
        thumbnail.loading = 'lazy';
        thumbnail.decoding = 'async';
        thumbnail.src = thumbFor(image);
        thumbnail.alt = image.alt || '';
        button.appendChild(thumbnail);
        button.addEventListener('click', () => {
          previousFocus = button;
          show(index);
        });
        strip.appendChild(button);
      });

      closeButton.addEventListener('click', close);
      lightbox.addEventListener('click', event => { if (event.target === lightbox) close(); });
      document.addEventListener('keydown', event => {
        if (!lightbox.classList.contains('is-visible')) return;
        if (event.key === 'Escape') close();
        if (event.key === 'ArrowLeft') move(-1);
        if (event.key === 'ArrowRight') move(1);
        if (event.key === 'Tab') {
          event.preventDefault();
          closeButton.focus();
        }
      });
    } catch (error) {
      console.error('[photos] Unable to load photography:', error);
    }
  });
})();