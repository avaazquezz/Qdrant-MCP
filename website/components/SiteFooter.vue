<script setup lang="ts">
import { useLanding } from '~/composables/useLanding'

const { copy, t } = useLanding()
</script>

<template>
  <footer class="on-panel border-t border-panel-line bg-panel text-panel-dim">
    <div class="mx-auto flex max-w-sheet flex-wrap items-center justify-between gap-x-8 gap-y-2 px-4 py-6 font-mono text-micro sm:px-6">
      <p>{{ copy.footer.license }} {{ copy.footer.independent }}</p>
      <p>{{ t(copy.footer.version) }} · {{ copy.footer.builtWith }}</p>
    </div>
  </footer>
</template>
