function binPackStub(items = [], options = {}) {
  if (options?.inPlace) {
    return {
      width: 0,
      height: 0,
      items,
    };
  }

  return {
    width: 0,
    height: 0,
    items: [...items],
  };
}

export default binPackStub;
