<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useVModel } from '@vueuse/core';
import {
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NFormItemGi,
  NGrid,
  NInput,
  NInputNumber,
  NSelect,
  NSwitch,
  useMessage
} from 'naive-ui';
import { fetchCreateAiModel, fetchUpdateAiModel } from '@/service/api';
import { $t } from '@/locales';

interface Props {
  visible: boolean;
  operateType: Api.OperateType;
  rowData?: Api.SystemManage.AiModel | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  'update:visible': [visible: boolean];
  submitted: [];
}>();

const message = useMessage();
const visible = useVModel(props, 'visible');

const formRef = ref();
const formRules = {
  name: { required: true, message: $t('form.required'), trigger: 'blur' },
  provider: { required: true, message: $t('form.required'), trigger: 'change' },
  base_url: { required: true, message: $t('form.required'), trigger: 'blur' },
  model_name: { required: true, message: $t('form.required'), trigger: 'blur' }
};

const defaultFormValue: Api.SystemManage.AiModelCreate = {
  name: '',
  provider: 'openai',
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  model_name: '',
  temperature: 0.7,
  max_tokens: null,
  is_default: '2',
  status: '1',
  remark: ''
};

const form = reactive<Api.SystemManage.AiModelCreate>({ ...defaultFormValue });

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic Claude', value: 'anthropic' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '通义千问', value: 'qwen' },
  { label: '智谱 GLM', value: 'zhipu' },
  { label: '自定义 (OpenAI 兼容)', value: 'custom' }
];

const providerDefaultBaseUrl: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com',
  deepseek: 'https://api.deepseek.com/v1',
  qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  zhipu: 'https://open.bigmodel.cn/api/paas/v4',
  custom: ''
};

const drawerTitle = computed(() => {
  return props.operateType === 'add' ? $t('page.manage.aiModel.addModel') : $t('page.manage.aiModel.editModel');
});

function handleProviderChange(value: string) {
  // 自动填充默认 base_url（仅当 base_url 为空或等于已知默认值时）
  const knownDefaults = Object.values(providerDefaultBaseUrl);
  if (!form.base_url || knownDefaults.includes(form.base_url)) {
    form.base_url = providerDefaultBaseUrl[value] || '';
  }
}

watch(
  () => props.visible,
  val => {
    if (val) {
      if (props.operateType === 'edit' && props.rowData) {
        form.name = props.rowData.name;
        form.provider = props.rowData.provider;
        form.base_url = props.rowData.base_url;
        form.api_key = '';
        form.model_name = props.rowData.model_name;
        form.temperature = props.rowData.temperature;
        form.max_tokens = props.rowData.max_tokens;
        form.is_default = props.rowData.is_default || '2';
        form.status = props.rowData.status || '1';
        form.remark = props.rowData.remark || '';
      } else {
        Object.assign(form, defaultFormValue);
      }
    }
  }
);

async function handleSubmit() {
  try {
    await formRef.value?.validate();
    if (props.operateType === 'add') {
      await fetchCreateAiModel(form);
      message.success($t('common.addSuccess'));
      emit('submitted');
      visible.value = false;
    } else if (props.operateType === 'edit' && props.rowData) {
      // 编辑时 api_key 留空表示不修改
      const updateData: Api.SystemManage.AiModelUpdate = { ...form };
      if (!form.api_key) {
        updateData.api_key = undefined;
      }
      await fetchUpdateAiModel(props.rowData.id, updateData);
      message.success($t('common.updateSuccess'));
      emit('submitted');
      visible.value = false;
    }
  } catch (error) {
    console.error('提交失败:', error);
  }
}
</script>

<template>
  <NDrawer v-model:show="visible" :width="520">
    <NDrawerContent :title="drawerTitle" closable>
      <NForm ref="formRef" :model="form" :rules="formRules" label-placement="top">
        <NGrid responsive="screen" item-responsive>
          <NFormItemGi span="24" :label="$t('page.manage.aiModel.modelName')" path="name">
            <NInput v-model:value="form.name" :placeholder="$t('page.manage.aiModel.form.modelName')" />
          </NFormItemGi>
          <NFormItemGi span="24 m:12" :label="$t('page.manage.aiModel.provider')" path="provider">
            <NSelect
              v-model:value="form.provider"
              :options="providerOptions"
              :placeholder="$t('page.manage.aiModel.form.provider')"
              @update:value="handleProviderChange"
            />
          </NFormItemGi>
          <NFormItemGi span="24 m:12" :label="$t('page.manage.aiModel.modelId')" path="model_name">
            <NInput v-model:value="form.model_name" :placeholder="$t('page.manage.aiModel.form.modelId')" />
          </NFormItemGi>
          <NFormItemGi span="24" :label="$t('page.manage.aiModel.baseUrl')" path="base_url">
            <NInput v-model:value="form.base_url" :placeholder="$t('page.manage.aiModel.form.baseUrl')" />
          </NFormItemGi>
          <NFormItemGi span="24" :label="$t('page.manage.aiModel.apiKey')" path="api_key">
            <NInput
              v-model:value="form.api_key"
              type="password"
              show-password-on="click"
              :placeholder="operateType === 'edit' ? $t('page.manage.aiModel.form.apiKeyEditHint') : $t('page.manage.aiModel.form.apiKey')"
            />
          </NFormItemGi>
          <NFormItemGi span="24 m:12" :label="$t('page.manage.aiModel.temperature')" path="temperature">
            <NInputNumber v-model:value="form.temperature" :step="0.1" :min="0" :max="2" class="w-full" />
          </NFormItemGi>
          <NFormItemGi span="24 m:12" :label="$t('page.manage.aiModel.maxTokens')" path="max_tokens">
            <NInputNumber v-model:value="form.max_tokens" :min="1" class="w-full" />
          </NFormItemGi>
          <NFormItemGi span="24" :label="$t('page.manage.aiModel.remark')" path="remark">
            <NInput v-model:value="form.remark" type="textarea" :rows="2" :placeholder="$t('page.manage.aiModel.form.remark')" />
          </NFormItemGi>
          <NFormItemGi span="24 m:12" :label="$t('page.manage.aiModel.isDefault')">
            <NSwitch
              :value="form.is_default === '1'"
              @update:value="val => (form.is_default = val ? '1' : '2')"
            />
          </NFormItemGi>
          <NFormItemGi span="24 m:12" :label="$t('page.manage.aiModel.status')">
            <NSwitch :value="form.status === '1'" @update:value="val => (form.status = val ? '1' : '2')" />
          </NFormItemGi>
        </NGrid>
      </NForm>
      <template #footer>
        <NSpace>
          <NButton @click="visible = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" @click="handleSubmit">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>

<style scoped></style>
