// assets/js/photos.js
(function () {
  const ready = (fn) =>
    document.readyState !== "loading"
      ? fn()
      : document.addEventListener("DOMContentLoaded", fn);

  ready(async () => {
    try {
      console.log("[photos] init");

      // Fetch manifest (relative so it works locally + on Pages)
      const res = await fetch("photos/manifest.json", { cache: "no-cache" });
      if (!res.ok) {
        console.warn("[photos] manifest fetch failed:", res.status, res.statusText);
        return;
      }
      const data = await res.json();
      const imgs = Array.isArray(data.images) ? data.images : Array.isArray(data) ? data : [];
      console.log("[photos] images:", imgs.length);
      if (!imgs.length) return;

      // Helpers
      const pick = (n, arr) => {
        const pool = arr.slice();
        const out = [];
        while (n-- > 0 && pool.length) {
          out.push(pool.splice(Math.floor(Math.random() * pool.length), 1)[0]);
        }
        return out;
      };
      const setBg = (el, src) => { if (el) el.style.backgroundImage = `url(${src})`; };

      // --- HERO BANNER ---
      (function hero() {
        const heroImg = document.querySelector(".hero-banner__img");
        if (!heroImg) return;
        const chosen =
          imgs.find(i => i.tone === "cool") ||
          imgs.find(i => i.tone === "neutral") ||
          imgs[0];
        const src = chosen.full || chosen.thumb;
        console.log("[photos] hero src:", src);
        heroImg.addEventListener("load", () => heroImg.classList.add("is-ready"));
        heroImg.src = src; // triggers load → adds .is-ready
      })();

      // --- FEATURED CARD COVERS ---
      (function covers() {
        const coverEls = document.querySelectorAll("[data-photo-slot^='card-']");
        if (!coverEls.length) return;
        pick(coverEls.length, imgs).forEach((p, i) => {
          setBg(coverEls[i], p.thumb || p.full);
        });
      })();

      // --- FILMSTRIP + LIGHTBOX ---
      (function filmstripAndLightbox() {
        const strip = document.querySelector("[data-photo-strip]");
        if (!strip) { console.warn("[photos] no [data-photo-strip]"); return; }

        const maxThumbs = Math.min(12, imgs.length);
        const selection = pick(maxThumbs, imgs);
        console.log("[photos] filmstrip picked:", selection.length);

        if (!selection.length) {
          strip.innerHTML = "<span class='muted'>No images available.</span>";
          return;
        }

        // Ensure lightbox exists (inject if missing)
        let lightbox = document.getElementById("lightbox");
        let lightboxImg = document.getElementById("lightboxImg");
        let lightboxClose = document.getElementById("lightboxClose");

        if (!lightbox) {
          const wrapper = document.createElement("div");
          wrapper.innerHTML = `
            <div class="lightbox" id="lightbox" aria-hidden="true">
              <span class="lightbox-close" id="lightboxClose" aria-label="Close">&times;</span>
              <img class="lightbox-img" id="lightboxImg" alt="">
            </div>`;
          document.body.appendChild(wrapper.firstElementChild);
          lightbox = document.getElementById("lightbox");
          lightboxImg = document.getElementById("lightboxImg");
          lightboxClose = document.getElementById("lightboxClose");
        }

        // Build thumbnails
        strip.innerHTML = "";
        selection.forEach((p, idx) => {
          const img = new Image();
          img.loading = "lazy";
          img.src = p.thumb || p.full;
          img.alt = p.alt || "";
          img.dataset.index = String(idx);
          img.addEventListener("click", () => openLightbox(idx));
          strip.appendChild(img);
        });

        let currentIndex = -1;

        function openLightbox(idx) {
          currentIndex = idx;
          const item = selection[currentIndex];
          const src = item.full || item.thumb;
          if (!src) return;
          lightboxImg.src = src;
          lightbox.classList.add("is-visible");
          lightbox.setAttribute("aria-hidden", "false");
        }

        function closeLightbox() {
          lightbox.classList.remove("is-visible");
          lightbox.setAttribute("aria-hidden", "true");
          lightboxImg.src = "";
          currentIndex = -1;
        }

        function nav(delta) {
          if (currentIndex < 0) return;
          currentIndex = (currentIndex + delta + selection.length) % selection.length;
          const item = selection[currentIndex];
          lightboxImg.src = item.full || item.thumb;
        }

        lightboxClose.addEventListener("click", closeLightbox);
        lightbox.addEventListener("click", (e) => { if (e.target === lightbox) closeLightbox(); });
        document.addEventListener("keydown", (e) => {
          if (!lightbox.classList.contains("is-visible")) return;
          if (e.key === "Escape") closeLightbox();
          if (e.key === "ArrowLeft") nav(-1);
          if (e.key === "ArrowRight") nav(1);
        });
      })();

    } catch (e) {
      console.error("[photos] error", e);
    }
  });
})();