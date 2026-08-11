<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NModal, NSpin } from 'naive-ui';

defineOptions({ name: 'NewsWebModal' });

interface Props {
  visible: boolean;
  url: string | null;
  title?: string;
}

interface Emits {
  (e: 'update:visible', visible: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const loading = ref(true);

const modalVisible = computed({
  get: () => props.visible,
  set: val => emit('update:visible', val)
});

watch(
  () => props.url,
  () => {
    loading.value = true;
  }
);

function onIframeLoad() {
  loading.value = false;
}

function openExternal() {
  if (props.url) {
    window.open(props.url, '_blank');
  }
}
</script>

<template>
  <NModal
    v-model:show="modalVisible"
    preset="card"
    :title="title"
    class="news-web-modal"
    :bordered="false"
    :style="{ width: '80%', maxWidth: '1100px' }"
  >
    <template #header-extra>
      <NButton size="small" type="primary" ghost @click="openExternal">
        <template #icon>
          <icon-ic-round-open-in-new class="text-icon" />
        </template>
        新窗口打开
      </NButton>
    </template>
    <div class="news-web-body">
      <NSpin v-if="loading" class="news-web-spin" />
      <iframe
        v-if="url"
        :src="url"
        class="news-web-iframe"
        sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
        @load="onIframeLoad"
      />
    </div>
  </NModal>
</template>

<style scoped>
.news-web-body {
  position: relative;
  height: 70vh;
  overflow: hidden;
}

.news-web-spin {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.news-web-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
