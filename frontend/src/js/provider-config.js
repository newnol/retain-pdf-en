export const DEFAULT_OCR_PROVIDER = "paddle";

export const OCR_PROVIDER_DEFINITIONS = [
  {
    id: "paddle",
    label: "PaddleOCR",
    description: "For PaddleOCR online OCR parsing.",
    tokenField: "paddle_token",
    runtimeConfigKey: "paddleToken",
    tokenLabel: "Paddle Access Token",
    tokenPlaceholder: "Enter Paddle Access Token",
    validationButtonLabel: "Check Paddle",
    validationIdleMessage: "You can check if the Paddle Access Token is valid.",
    validationMissingMessage: "Please enter the Paddle Access Token first.",
    validationUnavailableMessage: "",
    docsUrl: "https://aistudio.baidu.com/account/accessToken",
    docsLabel: "Get Token",
    supportsValidation: true,
  },
  {
    id: "mineru",
    label: "MinerU",
    description: "For OCR parsing and layout recognition.",
    tokenField: "mineru_token",
    runtimeConfigKey: "mineruToken",
    tokenLabel: "MinerU Token",
    tokenPlaceholder: "Enter MinerU Token",
    validationButtonLabel: "Check MinerU",
    validationIdleMessage: "The MinerU Token will be automatically validated before saving.",
    validationMissingMessage: "Please enter the MinerU Token first.",
    validationUnavailableMessage: "",
    docsUrl: "https://mineru.net/apiManage/docs?openApplyModal=true",
    docsLabel: "Get Token",
    supportsValidation: true,
  },
];

export const TRANSLATION_PROVIDER_DEFINITION = {
  id: "deepseek",
  label: "DeepSeek",
  keyLabel: "DeepSeek Key",
  keyPlaceholder: "Enter DeepSeek API Key",
  description: "For text translation and model calls.",
  docsUrl: "https://platform.deepseek.com/api_keys",
  docsLabel: "Get Key",
  validationButtonLabel: "Check DeepSeek",
    validationIdleMessage: "You can check if the DeepSeek API is reachable.",
  validationMissingMessage: "Please enter the DeepSeek Key first.",
  validationSuccessMessage: "DeepSeek API connection successful.",
  validationNetworkMessage: "DeepSeek API check failed, please check network or browser CORS restrictions.",
  validationUnauthorizedMessage: "DeepSeek Key is invalid or expired.",
};

export function normalizeOcrProvider(value) {
  const provider = `${value || ""}`.trim().toLowerCase();
  return OCR_PROVIDER_DEFINITIONS.some((item) => item.id === provider) ? provider : DEFAULT_OCR_PROVIDER;
}

export function getOcrProviderDefinition(provider) {
  return OCR_PROVIDER_DEFINITIONS.find((item) => item.id === normalizeOcrProvider(provider)) || OCR_PROVIDER_DEFINITIONS[0];
}
