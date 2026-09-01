<script setup lang="ts">
const badges = [
  {
    href: 'https://pypi.org/project/mcp-qdrant/',
    src: 'https://img.shields.io/pypi/v/mcp-qdrant.svg',
    alt: 'PyPI version',
  },
  {
    href: 'https://github.com/avaazquezz/Qdrant-MCP/actions/workflows/ci.yml',
    src: 'https://github.com/avaazquezz/Qdrant-MCP/actions/workflows/ci.yml/badge.svg',
    alt: 'CI status',
  },
  {
    href: 'https://pypi.org/project/mcp-qdrant/',
    src: 'https://img.shields.io/pypi/pyversions/mcp-qdrant.svg',
    alt: 'Python versions',
  },
  {
    href: 'https://github.com/avaazquezz/Qdrant-MCP/blob/main/LICENSE',
    src: 'https://img.shields.io/badge/license-MIT-blue.svg',
    alt: 'License: MIT',
  },
]
</script>

<template>
  <section class="border-b border-hairline py-5">
    <div class="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-x-8 gap-y-3 px-6">
      <span class="font-mono text-[10px] uppercase tracking-[0.2em] text-dust/70">verified —</span>
      <a
        v-for="badge in badges"
        :key="badge.alt"
        :href="badge.href"
        target="_blank"
        rel="noopener"
        class="opacity-80 grayscale transition-all hover:opacity-100 hover:grayscale-0"
      >
        <img :src="badge.src" :alt="badge.alt" class="h-5" />
      </a>
      <span class="font-mono text-[10px] uppercase tracking-[0.2em] text-dust/70">
        — built on the official qdrant-client sdk
      </span>
    </div>
  </section>
</template>
