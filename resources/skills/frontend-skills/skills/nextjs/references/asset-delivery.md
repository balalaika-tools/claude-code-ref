---
title: Use Next.js Asset Primitives Deliberately
impact: MEDIUM-HIGH
tags: image, font, script, lcp, cls, third-party
---

# Asset Delivery

## Images

Use `next/image` for images that benefit from responsive sizing, format conversion, lazy loading, or layout-shift prevention. Plain `<img>` remains reasonable for content that should not be optimized, such as tiny assets, some SVGs, or animated images.

- Provide meaningful `alt` text, or `alt=""` for decorative images.
- Use a static import when possible so dimensions and placeholders can be inferred.
- For remote images, provide dimensions or use `fill`, and allow only the required hosts and paths with narrow `remotePatterns`.
- When using `fill` or CSS-responsive sizing, provide an accurate `sizes` value; otherwise the browser may download an unnecessarily large source.
- In Next.js 16, use `preload` sparingly for the actual LCP image. The older `priority` prop is deprecated.
- Local image URLs containing query strings require a matching `images.localPatterns.search` configuration.

```tsx
<Image
  src={hero}
  alt="Product dashboard"
  sizes="(max-width: 768px) 100vw, 50vw"
  preload
/>
```

## Fonts

Use `next/font/google` or `next/font/local` to self-host font files, avoid browser requests to a third-party font service, and reduce layout shift. Prefer variable fonts when available. Define a reused font once and apply it at the narrowest layout that needs it; use the root layout for an application-wide font.

## Scripts

Use `next/script` for third-party scripts so their loading strategy is explicit:

- `beforeInteractive` only for rare scripts required before hydration.
- `afterInteractive` for scripts needed soon after hydration; this is the default.
- `lazyOnload` for non-critical work that can wait for browser idle time.
- Do not use the experimental `worker` strategy in App Router.

Place a script in the narrowest page or layout that needs it. Inline `Script` content requires a stable `id`. Event callbacks such as `onLoad`, `onReady`, and `onError` require a Client Component.

References: [Image optimization](https://nextjs.org/docs/app/getting-started/images), [Image component](https://nextjs.org/docs/app/api-reference/components/image), [Font optimization](https://nextjs.org/docs/app/getting-started/fonts), [Scripts](https://nextjs.org/docs/app/guides/scripts)
