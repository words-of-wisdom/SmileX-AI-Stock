<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NDescriptions, NDescriptionsItem, NDrawer, NDrawerContent, NSpace, NTag } from 'naive-ui';
import { fetchGetNewsDetail } from '@/service/api';
import { $t } from '@/locales';

defineOptions({
  name: 'NewsDetailDrawer'
});

interface Props {
  visible: boolean;
  newsId: number | null;
}

interface Emits {
  (e: 'update:visible', visible: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const loading = ref(false);
const detail = ref<Api.News.NewsDetail | null>(null);

const drawerVisible = computed({
  get: () => props.visible,
  set: val => emit('update:visible', val)
});

const tagType = computed<NaiveUI.ThemeColor>(() => 'info');

async function loadDetail(id: number) {
  loading.value = true;
  try {
    const { data, error } = await fetchGetNewsDetail(id);
    if (!error) {
      detail.value = data;
    }
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.newsId,
  id => {
    if (id !== null) {
      loadDetail(id);
    } else {
      detail.value = null;
    }
  }
);

function openOriginal() {
  if (detail.value?.url) {
    window.open(detail.value.url, '_blank');
  }
}
</script>

<template>
  <NDrawer v-model:show="drawerVisible" :width="640" placement="right">
    <NDrawerContent :title="$t('page.news.title')" closable :native-scrollbar="false">
      <div v-if="detail" class="flex-col-stretch gap-16px">
        <h2 class="text-20px font-500">{{ detail.title }}</h2>
        <NSpace align="center" :size="12">
          <NTag :type="tagType" size="small">{{ detail.source_name }}</NTag>
          <span v-if="detail.author" class="text-13px text-secondary">{{ detail.author }}</span>
          <span class="text-13px text-secondary">{{ detail.published_at || detail.created_at }}</span>
        </NSpace>
        <NDescriptions v-if="detail.summary" label-placement="left" :column="1" bordered size="small">
          <NDescriptionsItem :label="$t('page.news.summary')">{{ detail.summary }}</NDescriptionsItem>
        </NDescriptions>
        <div v-if="detail.content" class="whitespace-pre-wrap text-15px leading-relaxed">{{ detail.content }}</div>
        <div v-else-if="detail.summary" class="whitespace-pre-wrap text-15px leading-relaxed">{{ detail.summary }}</div>
      </div>
      <template #footer>
        <NButton type="primary" :disabled="!detail?.url" @click="openOriginal">
          {{ $t('page.news.viewOriginal') }}
        </NButton>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>

<style scoped></style>
