import { computed, onBeforeUnmount, ref, unref, watch } from "vue";

export function useDelayedReadyAnimation(isLoading, delay = 1000) {
  const exceededDelay = ref(false);
  let delayTimer = null;

  function clearDelayTimer() {
    if (!delayTimer) return;
    clearTimeout(delayTimer);
    delayTimer = null;
  }

  watch(
    isLoading,
    (loading) => {
      clearDelayTimer();
      if (!loading) return;

      exceededDelay.value = false;
      delayTimer = setTimeout(() => {
        exceededDelay.value = true;
        delayTimer = null;
      }, delay);
    },
    { immediate: true },
  );

  onBeforeUnmount(clearDelayTimer);

  return computed(() => !unref(isLoading) && exceededDelay.value);
}
