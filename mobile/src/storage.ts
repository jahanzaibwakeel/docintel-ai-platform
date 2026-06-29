import AsyncStorage from "@react-native-async-storage/async-storage";

const TOKEN_KEY = "docintel_token";
const REFRESH_TOKEN_KEY = "docintel_refresh_token";

export const tokenStorage = {
  get: () => AsyncStorage.getItem(TOKEN_KEY),
  getRefresh: () => AsyncStorage.getItem(REFRESH_TOKEN_KEY),
  set: (token: string) => AsyncStorage.setItem(TOKEN_KEY, token),
  setRefresh: (token: string) => AsyncStorage.setItem(REFRESH_TOKEN_KEY, token),
  setPair: async (accessToken: string, refreshToken: string) => {
    await AsyncStorage.multiSet([
      [TOKEN_KEY, accessToken],
      [REFRESH_TOKEN_KEY, refreshToken]
    ]);
  },
  clear: () => AsyncStorage.multiRemove([TOKEN_KEY, REFRESH_TOKEN_KEY])
};
