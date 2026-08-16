const ARABIC_TEXT = /[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]/u;

const MESSAGE_SELECTORS = [
  ".markdown",
  ".markdown-new-styling",
  ".prose",
  '[class*="_markdownRoot_"]',
  '[class*="_markdownContent_"]',
].join(",");

const INPUT_SELECTORS = 'textarea, [contenteditable="true"], [role="textbox"]';

function containsArabic(element) {
  return ARABIC_TEXT.test(element.innerText || element.textContent || "");
}

function updateDirection(element) {
  const isArabic = containsArabic(element);
  element.toggleAttribute("data-arabic-rtl", isArabic);
  if (isArabic) {
    element.setAttribute("dir", "rtl");
  } else if (element.matches(INPUT_SELECTORS)) {
    element.setAttribute("dir", "auto");
  }
}

function scan(root = document) {
  if (root instanceof Element && root.matches(`${MESSAGE_SELECTORS},${INPUT_SELECTORS}`)) {
    updateDirection(root);
  }
  root.querySelectorAll?.(`${MESSAGE_SELECTORS},${INPUT_SELECTORS}`).forEach(updateDirection);
}

const styles = document.createElement("style");
styles.textContent = `
  [data-arabic-rtl] {
    direction: rtl !important;
    text-align: right !important;
    unicode-bidi: plaintext;
  }

  [data-arabic-rtl] p,
  [data-arabic-rtl] h1,
  [data-arabic-rtl] h2,
  [data-arabic-rtl] h3,
  [data-arabic-rtl] h4,
  [data-arabic-rtl] h5,
  [data-arabic-rtl] h6,
  [data-arabic-rtl] li,
  [data-arabic-rtl] blockquote,
  [data-arabic-rtl] td,
  [data-arabic-rtl] th {
    direction: rtl !important;
    text-align: right !important;
  }

  [data-arabic-rtl] ul,
  [data-arabic-rtl] ol {
    padding-inline-start: 1.5rem !important;
    padding-inline-end: 0 !important;
  }

  [data-arabic-rtl] pre,
  [data-arabic-rtl] code,
  [data-arabic-rtl] kbd,
  [data-arabic-rtl] samp,
  [data-arabic-rtl] input[type="email"],
  [data-arabic-rtl] input[type="url"] {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: isolate;
  }

  [data-arabic-rtl] a {
    unicode-bidi: isolate;
  }
`;
document.head.appendChild(styles);

const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    const target = mutation.target instanceof Element
      ? mutation.target
      : mutation.target.parentElement;
    const directionalRoot = target?.closest?.(`${MESSAGE_SELECTORS},${INPUT_SELECTORS}`);
    if (directionalRoot) updateDirection(directionalRoot);
    mutation.addedNodes.forEach((node) => {
      if (node instanceof Element) scan(node);
    });
  }
});

function start() {
  scan();
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
  });
  document.addEventListener("input", (event) => {
    const input = event.target.closest?.(INPUT_SELECTORS);
    if (input) updateDirection(input);
  }, true);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start, { once: true });
} else {
  start();
}
