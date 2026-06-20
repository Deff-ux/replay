<template><span :class="['badge', status]">{{ status }}</span></template><script setup>defineProps({status:{type:String,default:'pending'}})</script>
