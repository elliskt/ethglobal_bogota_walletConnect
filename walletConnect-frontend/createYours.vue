<template>
  <div :class="
    time === 'night'
      ? 'createYours nightBgc nightColor borderNight animate__animated animate__fadeIn'
      : 'createYours morningBgc morningColor borderMorning animate__animated animate__fadeIn'
  ">
    <div class="wallet">
      <div class="backHome" @click="$router.push({ path: '/home' })">
        <span>← </span> <span> {{ $t("createYours.goBack") }}</span>
      </div>
      <h1>{{ $t("createYours.connect") }}</h1>
      <div class="walletContaner">
        <div :class="
          time === 'night' ? ' foxCard' : 'morningShowDow morningBgc foxCard'
        ">
          <div class="walletImg">
            <img src="@/assets/createYours/fox.svg" class="fox" alt="" />
          </div>
          <div class="walletText">
            <h4>Metamask</h4>
            <p>{{ $t("createYours.login") }}</p>
          </div>
          <div class="popular" @click="connectMetamask">
            <span>{{ $t("createYours.mostPopular") }}</span>
          </div>
        </div>
        <div :class="
          time === 'night' ? ' Beacon' : 'morningShowDow morningBgc beacon'
        ">
          <div class="walletImg">
            <img src="../assets/createYours/wifi.png" class="walletConnect" alt="">
          </div>
          <div class="walletText">
            <h4>{{ $t("createYours.walletConnect") }}</h4>
            <p>{{ $t("createYours.walletConnectDes") }}</p>
          </div>
          <div class="popular" @click="walletConnect">{{ $t("createYours.mostPopular") }}</div>
        </div>
        <div :class="
          time === 'night' ? ' Beacon' : 'morningShowDow morningBgc beacon'
        ">
          <div class="walletImg">
            <img src="../assets/createYours/logo-white.svg" class="beacon" alt="">
          </div>
          <div class="walletText">
            <h4>{{ $t("createYours.beacon") }}</h4>
            <p>{{ $t("createYours.beaconDes") }}</p>
          </div>
          <div class="popular" @click="connectBeacon">{{ $t("createYours.mostPopular") }}</div>
        </div>

      </div>
      <div class="NFTwallet">
        <p>{{ $t("createYours.note1") }}</p>
        <p>{{ $t("createYours.note2") }}</p>
        <p>{{ $t("createYours.note3") }}</p>
      </div>
    </div>
    <Footer></Footer>
  </div>
</template>

<script>
import Header from "@/components/header.vue";
import Footer from "@/components/footer.vue";
import global_ from "../components/global.vue";
import 'animate.css'
import { provider } from '../walletConnect/provider';
import { providers } from 'ethers'
const connectWalletConnect = async () => {
  try {
    await provider.enable();
    const web3Provider = new providers.Web3Provider(provider);
    const signer = await web3Provider.getSigner();
    const address = await signer.getAddress();
    console.log('this.state:', this.state);
    this.state.status = true;
    this.state.address = address;
    this.state.chainId = await provider.request({ method: "eth_chainId" });

    provider.on("disconnect", (code, reason) => {
      console.log("disconnected");
      this.state.status = false;
      state.address = "";
      localStorage.removeItem("userState");
    });

    provider.on("accountsChanged", (accounts) => {
      if (accounts.length > 0) {
        this.state.address = accounts[0];
        this.$router.push({
          path: "/home",
        });
      }
    });

    provider.on("chainChanged", (chainId) => {
      this.state.chainId = chainId;
    });
  } catch (error) {
    console.log(error);
  }
};
export default {
  props: ["time"],
  components: {
    Footer,
    Header,
  },
  data() {
    return {
      url: window.urls,
      language: window.localStorage.getItem("languageStorage") || "en",
      walletConnectFlag: false,
      state: {
        address: "",
        chainId: "",
        status: false,
      }
    };
  },
  watch: {
    walletConnectFlag(newValue) {
      console.log('walletConnectFlag有新值了:', newValue);
      if (newValue) {
        setTimeout(() => {
          $('#walletconnect-wrapper').css({ 'z-index': '99999999999999', 'opacity': '1' })
          if ($('#closeQrcodeModalBtn')) {
            $('#closeQrcodeModalBtn').remove();
            let closeBtn = '<div id="closeQrcodeModalBtn" style="opacity:0;z-index:999999;position: absolute;top: 0px;right: 0px;background: white;border-radius: 26px;padding: 6px;box-sizing: border-box;width: 26px;height: 26px;cursor: pointer; "></div>'
            $('.walletconnect-modal__header').append(closeBtn)
            $('#closeQrcodeModalBtn').on('click', () => {
              $('#walletconnect-wrapper').css({ 'z-index': '-1', 'opacity': '0' })
              this.walletConnectFlag = false;
            })
          }
        }, 500);
      }
    }
  },
  methods: {
    async connectWalletConnect() {
      try {
        await provider.enable();
        const web3Provider = new providers.Web3Provider(provider);
        const signer = await web3Provider.getSigner();
        const address = await signer.getAddress();
        console.log('this.state:', this.state);
        this.state.status = true;
        this.state.address = address;
        this.state.chainId = await provider.request({ method: "eth_chainId" });
        localStorage.setItem('userState', JSON.stringify(this.state));

        provider.on("disconnect", (code, reason) => {
          console.log("disconnected");
          this.state.status = false;
          state.address = "";
          localStorage.removeItem("userState");
        });

        provider.on("accountsChanged", (accounts) => {
          if (accounts.length > 0) {
            this.state.address = accounts[0];
            this.$store.commit("updateSwitchLang", false);
            this.$store.commit("updateShowAddress", true);
            this.$store.commit("updateConnectStatus", true);
            window.sessionStorage.connected = 1;
            global_.Connected = 1;
            this.$store.commit("updateWalletAddress", accounts[0]);
            this.$store.commit("updateMainAccount", accounts[0]);
            this.$router.push("/home");
          }
        });

        provider.on("chainChanged", (chainId) => {
          this.state.chainId = chainId;
        });
      } catch (error) {
        console.log(error);
      }
    },
    async walletConnect() {
      this.walletConnectFlag = true;
      await this.connectWalletConnect();
      if (JSON.parse(window.localStorage.userState).address !== '') {
        this.$store.commit("updateConnectStatus", true);
        window.sessionStorage.connected = 1;
        global_.Connected = 1;
        this.$store.commit("updateWalletAddress", JSON.parse(window.localStorage.userState).address);
        this.$store.commit("updateMainAccount", JSON.parse(window.localStorage.userState).address);
        this.$store.commit("updateSwitchLang", false);
        this.$store.commit("updateShowAddress", true);
        this.$router.push("/home");
      } else {
        this.$store.commit("updateConnectStatus", false);
        window.sessionStorage.connected = 0;
        global_.Connected = 0;
        this.$store.commit("updateWalletAddress", "Connect");
        this.$store.state.mainAccount = "";
        this.$store.commit("updateMainAccount", "");
        this.$store.commit("updateSwitchLang", true);
        this.$store.commit("updateShowAddress", false);
      }
    },
    async connectBeacon() {
      try {
        console.log("Requesting permissions...");
        const permissions = await window.dAppClient.requestPermissions();
        this.$store.state.mainAccount = permissions.address;
        this.$store.commit("updateConnectStatus", true);
        window.sessionStorage.connected = 1;
        global_.Connected = 1;
        this.$store.commit("updateWalletAddress", permissions.address);
        // 记录一下mainAccount
        this.$store.commit("updateMainAccount", permissions.address);
        this.$store.commit("updateSwitchLang", false);
        this.$store.commit("updateShowAddress", true);
        this.$router.push("/home");
        console.log("Got permissions:", permissions.address);
      } catch (error) {
        console.log("Got error:", error);
      }
    },
    async connectMetamask() {
      const address = await ethereum.request({
        method: "eth_accounts",
      });
      if (!address[0]) {
        await window.ethereum
          .request({
            method: "eth_requestAccounts",
          })
          .then((res, error) => {
            if (res) {
              this.$store.state.mainAccount = res[0];
              this.$store.commit("updateConnectStatus", true);
              window.sessionStorage.connected = 1;
              global_.Connected = 1;
              this.$store.commit("updateWalletAddress", address[0]);
              // 记录一下mainAccount
              this.$store.commit("updateMainAccount", address[0]);
              this.$store.commit("updateSwitchLang", false);
              this.$store.commit("updateShowAddress", true);
              this.$router.push("/home");
            } else {
            }
          });
      } else {
        this.$store.state.mainAccount = address[0];
        this.$store.commit("updateConnectStatus", true);
        window.sessionStorage.connected = 1;
        global_.Connected = 1;
        this.$store.commit("updateWalletAddress", address[0]);
        this.$store.commit("updateMainAccount", address[0]);
        this.$router.push("/home");
      }
      const address1 = await ethereum.request({
        method: "eth_accounts",
      });
      // 把地址传给后端记录每次钱包登录的时间
      this.$axios.post(this.url + "save_sincetime_info", {
        user_address: address1[0],
      });
      this.$axios.post(this.url + "retrieve_personal_collections", {
        user_address: address1[0],
      });
      this.$store.commit("updateMainAccount", address1[0]);
      this.$forceUpdate();
    },
  },
  computed: {
    // time: {
    //   get() {
    //     return this.$store.state.time;
    //   },
    //   set() {}
    // },
  },
};
</script>

<style lang="less" scoped>
@import "~@/assets/stylesheet/createYours.less";
</style>
