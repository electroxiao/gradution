<template>
  <span class="animated-title">{{ displayText }}</span>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  text: {
    type: String,
    default: "",
  },
  speed: {
    type: Number,
    default: 28,
  },
});

const displayText = ref(props.text);
let animationToken = 0;
let timer = null;

function sleep(ms) {
  return new Promise((resolve) => {
    timer = window.setTimeout(resolve, ms);
  });
}

function clearTimer() {
  if (timer !== null) {
    window.clearTimeout(timer);
    timer = null;
  }
}

function sharedPrefixLength(left, right) {
  const maxLength = Math.min(left.length, right.length);
  let index = 0;
  while (index < maxLength && left[index] === right[index]) {
    index += 1;
  }
  return index;
}

watch(
  () => props.text,
  async (nextText) => {
    const previousText = displayText.value;
    if (nextText === previousText) {
      return;
    }

    const shouldAnimate = previousText === "新对话" || previousText === "";
    if (!shouldAnimate) {
      displayText.value = nextText;
      return;
    }

    animationToken += 1;
    const currentToken = animationToken;
    clearTimer();

    const prefixLength = sharedPrefixLength(previousText, nextText);

    for (let index = previousText.length; index > prefixLength; index -= 1) {
      if (currentToken !== animationToken) {
        return;
      }
      displayText.value = previousText.slice(0, index - 1);
      await sleep(Math.max(12, props.speed / 2));
    }

    for (let index = prefixLength; index < nextText.length; index += 1) {
      if (currentToken !== animationToken) {
        return;
      }
      displayText.value = nextText.slice(0, index + 1);
      await sleep(props.speed);
    }

    if (currentToken === animationToken) {
      displayText.value = nextText;
      clearTimer();
    }
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  animationToken += 1;
  clearTimer();
});
</script>

<style scoped>
.animated-title {
  display: inline-block;
  min-width: 1ch;
  white-space: nowrap;
}
</style>
