<script setup lang="ts">
import { ref, toRaw } from 'vue';
import { jsonClone } from '@sa/utils';
import { $t } from '@/locales';
import { getGridActionSpan } from '@/utils/common';

defineOptions({
  name: 'NewsSearch'
});

interface Emits {
  (e: 'search'): void;
  (e: 'reset'): void;
}

const emit = defineEmits<Emits>();

const model = defineModel<Api.News.NewsSearchParams>('model', { required: true });

const defaultModel = jsonClone(toRaw(model.value));

const actionSpan = getGridActionSpan(2);

/** 日期范围本地态，提交时拆分为 start_time / end_time 写入 model */
const dateRange = ref<[string, string] | null>(
  model.value.start_time && model.value.end_time ? [model.value.start_time, model.value.end_time] : null
);

/** 将日期范围同步到搜索参数 */
function syncDateRange() {
  if (dateRange.value && dateRange.value.length === 2) {
    model.value.start_time = dateRange.value[0];
    model.value.end_time = dateRange.value[1];
  } else {
    model.value.start_time = null;
    model.value.end_time = null;
  }
}

function resetModel() {
  Object.assign(model.value, defaultModel);
  dateRange.value = null;
  emit('reset');
}

function search() {
  syncDateRange();
  emit('search');
}
</script>

<template>
  <NCard :bordered="false" size="small" class="card-wrapper">
    <NCollapse :default-expanded-names="['news-search']">
      <NCollapseItem :title="$t('common.search')" name="news-search">
        <NForm :model="model" label-placement="left" :label-width="80">
          <NGrid responsive="screen" item-responsive>
            <NFormItemGi span="24 s:12 m:6" :label="$t('common.title')" path="keyword" class="pr-24px">
              <NInput v-model:value="model.keyword" :placeholder="$t('page.news.form.keyword')" clearable />
            </NFormItemGi>
            <NFormItemGi span="24 s:12 m:12" :label="$t('page.news.dateRange')" path="dateRange" class="pr-24px">
              <NDatePicker
                v-model:value="dateRange"
                value-format="yyyy-MM-dd"
                type="daterange"
                clearable
                class="w-full"
              />
            </NFormItemGi>
            <NFormItemGi :span="actionSpan" class="pr-24px">
              <NSpace class="w-full" justify="end">
                <NButton @click="resetModel">
                  <template #icon>
                    <icon-ic-round-refresh class="text-icon" />
                  </template>
                  {{ $t('common.reset') }}
                </NButton>
                <NButton type="primary" ghost @click="search">
                  <template #icon>
                    <icon-ic-round-search class="text-icon" />
                  </template>
                  {{ $t('common.search') }}
                </NButton>
              </NSpace>
            </NFormItemGi>
          </NGrid>
        </NForm>
      </NCollapseItem>
    </NCollapse>
  </NCard>
</template>

<style scoped></style>
